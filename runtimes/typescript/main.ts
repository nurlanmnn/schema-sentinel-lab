import { runInventory } from "./inventory";
import { runTelemetry } from "./telemetry";
import { createServer, IncomingMessage } from "node:http";
import { Entity as EntityV1 } from "../../generated/ts/v1/entity";
import { Entity as EntityV2 } from "../../generated/ts/v2/entity";

const observationsHeader = "X-Schema-Sentinel-Observations";
const traceHeader = "X-Service-Trace";

export function processEntity(rawBytes: Uint8Array, version: string) {
  if (version !== "v1" && version !== "v2") throw new Error(`Unsupported schema version: ${version}`);
  // Plain Uint8Array selects the bounds-checked Reader rather than BufferReader.string clamping.
  rawBytes = new Uint8Array(rawBytes);
  const entity = version === "v1" ? EntityV1.decode(rawBytes) : EntityV2.decode(rawBytes);
  const fields = { entity_id: entity.entityId, ...(version === "v1" ? { name: (entity as EntityV1).name } : {}) };
  console.log(JSON.stringify({ runtime: "typescript", version, fields }));
  return { entity, fields };
}

async function readBody(request: IncomingMessage): Promise<Buffer> {
  const chunks: Buffer[] = [];
  for await (const chunk of request) chunks.push(Buffer.from(chunk));
  return Buffer.concat(chunks);
}

async function subscribe(): Promise<void> {
  const broker = process.env.PUBSUB_URL ?? "";
  if (!/^http:\/\/127\.0\.0\.1:\d+$/.test(broker)) throw new Error("PUBSUB_URL must be a loopback HTTP port");
  async function post(path: string, data: unknown) {
    const response = await fetch(broker + path, { method: "POST",
      headers: { "content-type": "application/json" }, body: JSON.stringify(data),
      signal: AbortSignal.timeout(5000) });
    if (!response.ok) throw new Error(`Broker returned ${response.status}: ${await response.text()}`);
    return response.json();
  }
  await post("/subscribe", { subscriber: "typescript", runtime: "typescript", topics: ["entity.v1", "entity.v2"] });
  while (true) {
    const { delivery } = await post("/poll", { subscriber: "typescript" });
    if (delivery === null) { await new Promise(resolve => setTimeout(resolve, 50)); continue; }
    if (delivery.topic !== "entity." + delivery.version) throw new Error("Topic/version mismatch");
    const { fields } = processEntity(Buffer.from(delivery.payload, "base64"), delivery.version);
    await post("/ack", { subscriber: "typescript", message_id: delivery.message_id, fields });
  }
}

if (process.argv.includes("--inventory")) {
  runInventory();
} else if (process.argv.includes("--telemetry")) {
  runTelemetry();
} else if (process.argv.includes("--subscribe")) {
  subscribe().catch(error => { console.error(error); process.exitCode = 1; });
} else if (process.argv.includes("--serve")) {
  createServer(async (request, response) => {
    if (request.method === "GET" && request.url === "/health") {
      response.writeHead(200, { "content-type": "application/json" });
      response.end(JSON.stringify({ status: "ok", runtime: "typescript" }));
      return;
    }
    if (request.method !== "POST" || request.url !== "/relay") {
      response.writeHead(404); response.end(); return;
    }
    try {
      const { entity, fields } = processEntity(await readBody(request), "v1");
      const trace = JSON.parse(String(request.headers[traceHeader.toLowerCase()] ?? "[]"));
      trace.push("typescript");
      const downstream = await fetch(process.env.CSHARP_RELAY_URL ?? "http://localhost:8002/relay", {
        method: "POST",
        headers: { "content-type": "application/x-protobuf", [traceHeader]: JSON.stringify(trace) },
        body: Buffer.from(EntityV1.encode(entity as EntityV1).finish()),
        signal: AbortSignal.timeout(5000),
      });
      if (!downstream.ok) throw new Error(`C# relay returned ${downstream.status}`);
      const body = Buffer.from(await downstream.arrayBuffer());
      const observations = [{ runtime: "typescript", fields }, ...JSON.parse(downstream.headers.get(observationsHeader) ?? "null")];
      response.writeHead(200, {
        "content-type": "application/x-protobuf", "content-length": body.length,
        [observationsHeader]: JSON.stringify(observations).replace(/[\u007f-\uffff]/g, c => `\\u${c.charCodeAt(0).toString(16).padStart(4, "0")}`),
        [traceHeader]: downstream.headers.get(traceHeader) ?? "[]",
      });
      response.end(body);
    } catch (error) {
      response.writeHead(400, { "content-type": "application/json" });
      response.end(JSON.stringify({ error: String(error) }));
    }
  }).listen(Number(process.env.PORT ?? "8001"), "0.0.0.0");
} else {
  const version = process.argv.includes("--v2") ? "v2" : "v1";
  const bytes = version === "v1"
    ? EntityV1.encode({ entityId: "ts_303", name: "Sensor C" }).finish()
    : EntityV2.encode({ entityId: "ts_303" }).finish();
  processEntity(bytes, version);
}
