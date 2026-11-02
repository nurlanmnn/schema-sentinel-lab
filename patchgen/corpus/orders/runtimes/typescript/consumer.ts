import { Order } from "./generated/orders";
export const sample = () => Order.create({ orderId: "O-1", amountCents: 1250, currency: "USD" });
export const observe = (order: Order) => ({ amount_cents: order.amountCents, currency: order.currency });
export const isUsd = (order: Order) => order.currency === "USD";
