using System.Text.Json;
using Google.Protobuf;

static class TelemetryRuntime
{
    public static void Run()
    {
        var requests = JsonSerializer.Deserialize<TelemetryRequest[]>(Console.In.ReadToEnd(),
            new JsonSerializerOptions(JsonSerializerDefaults.Web)) ?? throw new JsonException("Missing requests");
        var results = requests.Select(request => {
            var entity = Simulation.Telemetry.VehicleTelemetry.Parser.ParseFrom(Convert.FromBase64String(request.Payload));
            var sample = new Simulation.Telemetry.VehicleTelemetry { VehicleId = request.VehicleId, SpeedMps = request.Speed };
            var fields = new Dictionary<string, object> { ["vehicle_id"] = entity.VehicleId, ["speed_mps"] = entity.SpeedMps };
            return new { fields, speeding = entity.SpeedMps > 30.0, constructed_payload = Convert.ToBase64String(sample.ToByteArray()) };
        });
        Console.WriteLine(JsonSerializer.Serialize(results));
    }
}
record TelemetryRequest(string Payload, [property: System.Text.Json.Serialization.JsonPropertyName("vehicle_id")] string VehicleId, float Speed);
