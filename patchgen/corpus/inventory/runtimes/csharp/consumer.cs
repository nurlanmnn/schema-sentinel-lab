using Demo.Inventory;
class InventoryReader {
    static StockItem Sample() => new StockItem { Sku = "A-1", Quantity = 24, Labels = { "fragile" }, State = StockState.StockAvailable };
    static object Observe(StockItem item) => new { quantity = item.Quantity, labels = item.Labels, state = item.State };
    static bool CanFulfill(StockItem item, int requested) => item.Quantity >= requested && item.State == StockState.StockAvailable;
}
