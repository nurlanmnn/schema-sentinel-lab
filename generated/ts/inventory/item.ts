/* eslint-disable */
import * as _m0 from "protobufjs/minimal";

export const protobufPackage = "simulation.inventory";

export interface StockItem {
  sku: string;
  quantity: number;
}

function createBaseStockItem(): StockItem {
  return { sku: "", quantity: 0 };
}

export const StockItem = {
  encode(message: StockItem, writer: _m0.Writer = _m0.Writer.create()): _m0.Writer {
    if (message.sku !== "") {
      writer.uint32(10).string(message.sku);
    }
    if (message.quantity !== 0) {
      writer.uint32(16).int32(message.quantity);
    }
    return writer;
  },

  decode(input: _m0.Reader | Uint8Array, length?: number): StockItem {
    const reader = input instanceof _m0.Reader ? input : _m0.Reader.create(input);
    let end = length === undefined ? reader.len : reader.pos + length;
    const message = createBaseStockItem();
    while (reader.pos < end) {
      const tag = reader.uint32();
      switch (tag >>> 3) {
        case 1:
          if (tag !== 10) {
            break;
          }

          message.sku = reader.string();
          continue;
        case 2:
          if (tag !== 16) {
            break;
          }

          message.quantity = reader.int32();
          continue;
      }
      if ((tag & 7) === 4 || tag === 0) {
        break;
      }
      reader.skipType(tag & 7);
    }
    return message;
  },

  fromJSON(object: any): StockItem {
    return {
      sku: isSet(object.sku) ? globalThis.String(object.sku) : "",
      quantity: isSet(object.quantity) ? globalThis.Number(object.quantity) : 0,
    };
  },

  toJSON(message: StockItem): unknown {
    const obj: any = {};
    if (message.sku !== "") {
      obj.sku = message.sku;
    }
    if (message.quantity !== 0) {
      obj.quantity = Math.round(message.quantity);
    }
    return obj;
  },

  create<I extends Exact<DeepPartial<StockItem>, I>>(base?: I): StockItem {
    return StockItem.fromPartial(base ?? ({} as any));
  },
  fromPartial<I extends Exact<DeepPartial<StockItem>, I>>(object: I): StockItem {
    const message = createBaseStockItem();
    message.sku = object.sku ?? "";
    message.quantity = object.quantity ?? 0;
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
