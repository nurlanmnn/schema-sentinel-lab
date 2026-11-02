/* eslint-disable */
import * as _m0 from "protobufjs/minimal";

export const protobufPackage = "simulation.telemetry";

export interface VehicleTelemetry {
  vehicleId: string;
  /** Ground speed in meters per second. */
  speedMps: number;
}

function createBaseVehicleTelemetry(): VehicleTelemetry {
  return { vehicleId: "", speedMps: 0 };
}

export const VehicleTelemetry = {
  encode(message: VehicleTelemetry, writer: _m0.Writer = _m0.Writer.create()): _m0.Writer {
    if (message.vehicleId !== "") {
      writer.uint32(10).string(message.vehicleId);
    }
    if (message.speedMps !== 0) {
      writer.uint32(21).float(message.speedMps);
    }
    return writer;
  },

  decode(input: _m0.Reader | Uint8Array, length?: number): VehicleTelemetry {
    const reader = input instanceof _m0.Reader ? input : _m0.Reader.create(input);
    let end = length === undefined ? reader.len : reader.pos + length;
    const message = createBaseVehicleTelemetry();
    while (reader.pos < end) {
      const tag = reader.uint32();
      switch (tag >>> 3) {
        case 1:
          if (tag !== 10) {
            break;
          }

          message.vehicleId = reader.string();
          continue;
        case 2:
          if (tag !== 21) {
            break;
          }

          message.speedMps = reader.float();
          continue;
      }
      if ((tag & 7) === 4 || tag === 0) {
        break;
      }
      reader.skipType(tag & 7);
    }
    return message;
  },

  fromJSON(object: any): VehicleTelemetry {
    return {
      vehicleId: isSet(object.vehicleId) ? globalThis.String(object.vehicleId) : "",
      speedMps: isSet(object.speedMps) ? globalThis.Number(object.speedMps) : 0,
    };
  },

  toJSON(message: VehicleTelemetry): unknown {
    const obj: any = {};
    if (message.vehicleId !== "") {
      obj.vehicleId = message.vehicleId;
    }
    if (message.speedMps !== 0) {
      obj.speedMps = message.speedMps;
    }
    return obj;
  },

  create<I extends Exact<DeepPartial<VehicleTelemetry>, I>>(base?: I): VehicleTelemetry {
    return VehicleTelemetry.fromPartial(base ?? ({} as any));
  },
  fromPartial<I extends Exact<DeepPartial<VehicleTelemetry>, I>>(object: I): VehicleTelemetry {
    const message = createBaseVehicleTelemetry();
    message.vehicleId = object.vehicleId ?? "";
    message.speedMps = object.speedMps ?? 0;
    return message;
  },
};

type Builtin = Date | Function | Uint8Array | string | number | boolean | undefined;

export type DeepPartial<T> = T extends Builtin ? T
  : T extends globalThis.Array<infer U> ? globalThis.Array<DeepPartial<U>>
  : T extends ReadonlyArray<infer U> ? ReadonlyArray<DeepPartial<U>>
  : T extends {} ? { [K in keyof T]?: DeepPartial<T[K]> }
  : Partial<T>;

type KeysOfUnion<T> = T extends T ? keyof T : never;
export type Exact<P, I extends P> = P extends Builtin ? P
  : P & { [K in keyof P]: Exact<P[K], I[K]> } & { [K in Exclude<keyof I, KeysOfUnion<P>>]: never };

function isSet(value: any): boolean {
  return value !== null && value !== undefined;
}
