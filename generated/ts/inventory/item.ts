/* eslint-disable */
import * as _m0 from "protobufjs/minimal";

export const protobufPackage = "simulation.inventory";

export enum StockState {
  STOCK_STATE_UNSPECIFIED = 0,
  STOCK_STATE_QUARANTINED = 1,
  UNRECOGNIZED = -1,
}

export function stockStateFromJSON(object: any): StockState {
  switch (object) {
    case 0:
    case "STOCK_STATE_UNSPECIFIED":
      return StockState.STOCK_STATE_UNSPECIFIED;
    case 1:
    case "STOCK_STATE_QUARANTINED":
      return StockState.STOCK_STATE_QUARANTINED;
    case -1:
    case "UNRECOGNIZED":
    default:
      return StockState.UNRECOGNIZED;
  }
}

export function stockStateToJSON(object: StockState): string {
  switch (object) {
    case StockState.STOCK_STATE_UNSPECIFIED:
      return "STOCK_STATE_UNSPECIFIED";
    case StockState.STOCK_STATE_QUARANTINED:
      return "STOCK_STATE_QUARANTINED";
    case StockState.UNRECOGNIZED:
    default:
      return "UNRECOGNIZED";
  }
}

export interface StockItem {
  sku: string;
  quantity: number;
  state: StockState;
  displayLabels: string[];
  binCounts: number[];
  warehouse: string;
  dropZone: string;
}

function createBaseStockItem(): StockItem {
  return { sku: "", quantity: 0, state: 0, displayLabels: [], binCounts: [], warehouse: "", dropZone: "" };
}

export const StockItem = {
  encode(message: StockItem, writer: _m0.Writer = _m0.Writer.create()): _m0.Writer {
    if (message.sku !== "") {
      writer.uint32(10).string(message.sku);
    }
    if (message.quantity !== 0) {
      writer.uint32(16).int32(message.quantity);
    }
    if (message.state !== 0) {
      writer.uint32(24).int32(message.state);
    }
    for (const v of message.displayLabels) {
      writer.uint32(34).string(v!);
    }
    writer.uint32(50).fork();
    for (const v of message.binCounts) {
      writer.int32(v);
    }
    writer.ldelim();
    if (message.warehouse !== "") {
      writer.uint32(58).string(message.warehouse);
    }
    if (message.dropZone !== "") {
      writer.uint32(66).string(message.dropZone);
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
        case 3:
          if (tag !== 24) {
            break;
          }

          message.state = reader.int32() as any;
          continue;
        case 4:
          if (tag !== 34) {
            break;
          }

          message.displayLabels.push(reader.string());
          continue;
        case 6:
          if (tag === 48) {
            message.binCounts.push(reader.int32());

            continue;
          }

          if (tag === 50) {
            const end2 = reader.uint32() + reader.pos;
            while (reader.pos < end2) {
              message.binCounts.push(reader.int32());
            }

            continue;
          }

          break;
        case 7:
          if (tag !== 58) {
            break;
          }

          message.warehouse = reader.string();
          continue;
        case 8:
          if (tag !== 66) {
            break;
          }

          message.dropZone = reader.string();
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
      state: isSet(object.state) ? stockStateFromJSON(object.state) : 0,
      displayLabels: globalThis.Array.isArray(object?.displayLabels)
        ? object.displayLabels.map((e: any) => globalThis.String(e))
        : [],
      binCounts: globalThis.Array.isArray(object?.binCounts)
        ? object.binCounts.map((e: any) => globalThis.Number(e))
        : [],
      warehouse: isSet(object.warehouse) ? globalThis.String(object.warehouse) : "",
      dropZone: isSet(object.dropZone) ? globalThis.String(object.dropZone) : "",
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
    if (message.state !== 0) {
      obj.state = stockStateToJSON(message.state);
    }
    if (message.displayLabels?.length) {
      obj.displayLabels = message.displayLabels;
    }
    if (message.binCounts?.length) {
      obj.binCounts = message.binCounts.map((e) => Math.round(e));
    }
    if (message.warehouse !== "") {
      obj.warehouse = message.warehouse;
    }
    if (message.dropZone !== "") {
      obj.dropZone = message.dropZone;
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
    message.state = object.state ?? 0;
    message.displayLabels = object.displayLabels?.map((e) => e) || [];
    message.binCounts = object.binCounts?.map((e) => e) || [];
    message.warehouse = object.warehouse ?? "";
    message.dropZone = object.dropZone ?? "";
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
