from generated.telemetry_pb2 import VehicleTelemetry

def sample():
    return VehicleTelemetry(vehicle_id="car-1", speed_mps=12.5)
def observe(entity):
    return {"vehicle_id": entity.vehicle_id, "speed_mps": entity.speed_mps}
def speeding(entity):
    return entity.speed_mps > 30.0
