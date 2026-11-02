from generated.inventory_pb2 import StockItem, STOCK_AVAILABLE

def sample():
    return StockItem(sku="A-1", quantity=24, labels=["fragile"], state=STOCK_AVAILABLE)
def observe(item):
    return {"quantity": item.quantity, "labels": list(item.labels), "state": item.state}
def can_fulfill(item, requested):
    return item.quantity >= requested and item.state == STOCK_AVAILABLE
