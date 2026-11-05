import { readFileSync } from "node:fs";
import { StockItem, StockState } from "../../generated/ts/inventory/item";

interface Request { payload: string; sku: string; quantity: string; display_labels?: string[]; include_state?: boolean; warehouse?: string; drop_zone?: string; include_route?: boolean }
function stateLabel(state: StockState) {
  switch (state) {
    case StockState.STOCK_STATE_UNSPECIFIED: return "UNSPECIFIED";
    case StockState.STOCK_STATE_QUARANTINED: return "QUARANTINED";
    default: return "UNKNOWN";
  }
}
export function runInventory() {
  const requests: Request[] = JSON.parse(readFileSync(0, "utf8"));
  const results = requests.map(request => {
    const entity = StockItem.decode(new Uint8Array(Buffer.from(request.payload, "base64")));
    const sample = StockItem.encode({ sku: request.sku, quantity: Number.parseInt(request.quantity, 10), state: StockState.STOCK_STATE_UNSPECIFIED,
      displayLabels: request.display_labels ?? [],
      warehouse: request.warehouse ?? "", dropZone: request.drop_zone ?? "" }).finish();
    const fields = {
      sku: entity.sku, quantity: entity.quantity.toString(),
      ...(request.display_labels === undefined ? {} : { display_labels: entity.displayLabels }),
      ...(request.include_route ? { warehouse: entity.warehouse, drop_zone: entity.dropZone } : {}),
      ...(request.include_state ? { state_label: stateLabel(entity.state) } : {}),
    };
    return { fields, in_stock: BigInt(entity.quantity) > 0n && entity.state === StockState.STOCK_STATE_UNSPECIFIED, constructed_payload: Buffer.from(sample).toString("base64") };
  });
  console.log(JSON.stringify(results));
}
