import { VehicleTelemetry } from "./generated/telemetry";
export const sample = () => VehicleTelemetry.create({ vehicleId: "car-1", speedMps: 12.5 });
export const observe = (entity: VehicleTelemetry) => ({ vehicle_id: entity.vehicleId, speed_mps: entity.speedMps });
export const speeding = (entity: VehicleTelemetry) => entity.speedMps > 30.0;
