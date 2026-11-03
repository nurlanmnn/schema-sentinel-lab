/* eslint-disable */
import * as _m0 from "protobufjs/minimal";

export const protobufPackage = "fleet";

export interface Vehicle {
  speedMps: number;
}

function createBaseVehicle(): Vehicle {
  return { speedMps: 0 };
}

export const Vehicle = {
  encode(message: Vehicle, writer: _m0.Writer = _m0.Writer.create()): _m0.Writer {
    if (message.speedMps !== 0) {
      writer.uint32(13).float(message.speedMps);
    }
    return writer;
  },

  decode(input: _m0.Reader | Uint8Array, length?: number): Vehicle {
    const reader = input instanceof _m0.Reader ? input : _m0.Reader.create(input);
    let end = length === undefined ? reader.len : reader.pos + length;
    const message = createBaseVehicle();
    while (reader.pos < end) {
      const tag = reader.uint32();
      switch (tag >>> 3) {
        case 1:
          if (tag !== 13) {
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

  fromJSON(object: any): Vehicle {
    return { speedMps: isSet(object.speedMps) ? globalThis.Number(object.speedMps) : 0 };
  },

  toJSON(message: Vehicle): unknown {
    const obj: any = {};
    if (message.speedMps !== 0) {
      obj.speedMps = message.speedMps;
    }
    return obj;
  },

  create<I extends Exact<DeepPartial<Vehicle>, I>>(base?: I): Vehicle {
    return Vehicle.fromPartial(base ?? ({} as any));
  },
  fromPartial<I extends Exact<DeepPartial<Vehicle>, I>>(object: I): Vehicle {
    const message = createBaseVehicle();
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
