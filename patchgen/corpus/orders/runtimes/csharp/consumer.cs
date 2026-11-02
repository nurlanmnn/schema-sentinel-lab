using Demo.Orders;
class OrderReader {
    static Order Sample() => new Order { OrderId = "O-1", AmountCents = 1250, Currency = "USD" };
    static object Observe(Order order) => new { amount_cents = order.AmountCents, currency = order.Currency };
    static bool IsUsd(Order order) => order.Currency == "USD";
}
