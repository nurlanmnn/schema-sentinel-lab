import { StockItem, StockState } from "./generated/inventory";
export const sample = () => StockItem.create({ sku: "A-1", quantity: 24, labels: ["fragile"], state: StockState.STOCK_AVAILABLE });
export const observe = (item: StockItem) => ({ quantity: item.quantity, labels: item.labels, state: item.state });
export const canFulfill = (item: StockItem, requested: number) => item.quantity >= requested && item.state === StockState.STOCK_AVAILABLE;
