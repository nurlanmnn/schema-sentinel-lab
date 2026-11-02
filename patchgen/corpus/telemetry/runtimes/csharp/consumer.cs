using Demo.Telemetry;
class TelemetryReader {
    static VehicleTelemetry Sample() => new VehicleTelemetry { VehicleId = "car-1", SpeedMps = 12.5f };
    static object Observe(VehicleTelemetry entity) => new { vehicle_id = entity.VehicleId, speed_mps = entity.SpeedMps };
    static bool Speeding(VehicleTelemetry entity) => entity.SpeedMps > 30.0f;
}
