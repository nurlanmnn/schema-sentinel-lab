import { readFileSync } from "node:fs";
import { StockItem } from "../../generated/ts/inventory/item";

interface Request { payload: string; sku: string; quantity: string }
export function runInventory() {
  const requests: Request[] = JSON.parse(readFileSync(0, "utf8"));
  const results = requests.map(request => {
    const entity = StockItem.decode(new Uint8Array(Buffer.from(request.payload, "base64")));
    const sample = StockItem.encode({ sku: request.sku, quantity: Number.parseInt(request.quantity, 10) }).finish();
    const fields = { sku: entity.sku, quantity: entity.quantity.toString() };
    return { fields, in_stock: BigInt(entity.quantity) > 0n, constructed_payload: Buffer.from(sample).toString("base64") };
  });
  console.log(JSON.stringify(results));
}
