from generated.orders_pb2 import Order

def sample():
    return Order(order_id="O-1", amount_cents=1250, currency="USD")
def observe(order):
    return {"amount_cents": order.amount_cents, "currency": order.currency}
def is_usd(order):
    return order.currency == "USD"
