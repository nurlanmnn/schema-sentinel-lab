using System.Text.Json;
using Google.Protobuf;

const string observationsHeader = "X-Schema-Sentinel-Observations";
const string traceHeader = "X-Service-Trace";

static (IMessage Entity, Dictionary<string, string> Fields) ProcessEntity(byte[] rawBytes, string version)
{
    IMessage entity;
    Dictionary<string, string> fields;
    if (version == "v1")
    {
        var decoded = Simulation.V1.Entity.Parser.ParseFrom(rawBytes);
        entity = decoded;
        fields = new() { ["entity_id"] = decoded.EntityId, ["name"] = decoded.Name };
    }
    else if (version == "v2")
    {
        var decoded = Simulation.V2.Entity.Parser.ParseFrom(rawBytes);
        entity = decoded;
        fields = new() { ["entity_id"] = decoded.EntityId };
    }
    else throw new ArgumentException($"Unsupported version: {version}");
    Console.WriteLine(JsonSerializer.Serialize(new { runtime = "csharp", version, fields }));
    return (entity, fields);
}

if (args.Contains("--subscribe"))
{
    var broker = Environment.GetEnvironmentVariable("PUBSUB_URL") ?? "";
    if (!System.Text.RegularExpressions.Regex.IsMatch(broker, @"^http://127\.0\.0\.1:\d+$"))
        throw new ArgumentException("PUBSUB_URL must be a loopback HTTP port");
    using var client = new HttpClient { BaseAddress = new Uri(broker), Timeout = TimeSpan.FromSeconds(5) };
    async Task<string> Post(string path, object data)
    {
        using var content = new StringContent(JsonSerializer.Serialize(data), System.Text.Encoding.UTF8, "application/json");
        using var response = await client.PostAsync(path, content);
        if (!response.IsSuccessStatusCode)
            throw new HttpRequestException($"Broker returned {response.StatusCode}: {await response.Content.ReadAsStringAsync()}");
        return await response.Content.ReadAsStringAsync();
    }
    await Post("/subscribe", new { subscriber = "csharp", runtime = "csharp", topics = new[] { "entity.v1", "entity.v2" } });
    while (true)
    {
        var poll = JsonSerializer.Deserialize<PubsubPoll>(await Post("/poll", new { subscriber = "csharp" }),
            new JsonSerializerOptions(JsonSerializerDefaults.Web)) ?? throw new JsonException("Missing poll envelope");
        var delivery = poll.Delivery;
        if (delivery is null) { await Task.Delay(50); continue; }
        var version = delivery.Version;
        if (delivery.Topic != "entity." + version)
            throw new ArgumentException("Topic/version mismatch");
        var (_, fields) = ProcessEntity(Convert.FromBase64String(delivery.Payload), version);
        await Post("/ack", new { subscriber = "csharp", message_id = delivery.MessageId, fields });
    }
}

if (args.Contains("--inventory"))
{
    InventoryRuntime.Run();
    return 0;
}
if (args.Contains("--telemetry"))
{
    TelemetryRuntime.Run();
    return 0;
}
if (args.Contains("--healthcheck"))
{
    using var client = new HttpClient { Timeout = TimeSpan.FromSeconds(1) };
    try { return (await client.GetAsync("http://localhost:8002/health")).IsSuccessStatusCode ? 0 : 1; }
    catch (Exception error) when (error is HttpRequestException or TaskCanceledException) { return 1; }
}
if (!args.Contains("--serve"))
{
    var version = args.Contains("--v2") ? "v2" : "v1";
    IMessage entity = version == "v1"
        ? new Simulation.V1.Entity { EntityId = "cs_202", Name = "Sensor B" }
        : new Simulation.V2.Entity { EntityId = "cs_202" };
    ProcessEntity(entity.ToByteArray(), version);
    return 0;
}
var builder = WebApplication.CreateBuilder(args.Where(arg => arg != "--serve").ToArray());
var app = builder.Build();
app.MapGet("/health", () => Results.Json(new { status = "ok", runtime = "csharp" }));
app.MapPost("/relay", async (HttpRequest request, HttpResponse response) =>
{
    try
    {
        using var body = new MemoryStream();
        await request.Body.CopyToAsync(body);
        var (entity, fields) = ProcessEntity(body.ToArray(), "v1");
        var trace = JsonSerializer.Deserialize<List<string>>(request.Headers[traceHeader].FirstOrDefault() ?? "[]")
            ?? throw new JsonException("Trace must be an array");
        trace.Add("csharp");
        response.Headers[observationsHeader] = JsonSerializer.Serialize(new[] { new { runtime = "csharp", fields } });
        response.Headers[traceHeader] = JsonSerializer.Serialize(trace);
        response.ContentType = "application/x-protobuf";
        await response.Body.WriteAsync(entity.ToByteArray());
    }
    catch (Exception error) when (error is InvalidProtocolBufferException or JsonException)
    {
        response.StatusCode = 400;
        await response.WriteAsJsonAsync(new { error = error.Message });
    }
});
app.Run();
return 0;

record PubsubPoll(PubsubDelivery? Delivery);
record PubsubDelivery([property: System.Text.Json.Serialization.JsonPropertyName("message_id")] int MessageId, string Topic, string Version, string Payload);
