import { readFileSync } from "node:fs";
import { VehicleTelemetry } from "../../generated/ts/telemetry/vehicle";

interface Request { payload: string; vehicle_id: string; speed: number }
export function runTelemetry() {
  const requests: Request[] = JSON.parse(readFileSync(0, "utf8"));
  const results = requests.map(request => {
    const entity = VehicleTelemetry.decode(new Uint8Array(Buffer.from(request.payload, "base64")));
    const sample = VehicleTelemetry.encode({ vehicleId: request.vehicle_id, speedMps: request.speed }).finish();
    const fields = { vehicle_id: entity.vehicleId, speed_mps: entity.speedMps };
    return { fields, speeding: entity.speedMps > 30.0, constructed_payload: Buffer.from(sample).toString("base64") };
  });
  console.log(JSON.stringify(results));
}
