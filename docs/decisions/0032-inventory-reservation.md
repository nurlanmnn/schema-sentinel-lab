# 0032. Account for reserved inventory when computing availability

The pinned migration adds `int32 reserved_quantity = 5` to `StockItem`.
Existing requests and wire payloads default to zero reservations. Producers
accept the optional integer and keep total quantity as a decimal string.
Consumers consider stock eligible when the state is unspecified, reserved
quantity is nonnegative, and total quantity exceeds reserved quantity.
Comparing the quantities directly avoids subtraction overflow.

The detector recognizes the addition of a plain implicit proto3 int32
with canonical JSON metadata. The generic locator can report syntax
candidates for the added name. The pinned policy explicitly anchors its
scan to the existing quantity field because it owns the affected
construction and availability rules. The scan still reports candidates and
the proposal requires each authored edit site.

The independent oracle checks old payloads, fully reserved and oversold
stock, negative reservations, signed int32 boundaries, and quarantined and
unknown states. The producer reservation differs from the consumer value.
Checks compare the exact serialized bytes and existing observation shape
across Python, TypeScript and C#.

Upgrade readers before sending reservations. Old readers ignore field 5
and can overstate availability. New readers still handle old payloads with
the zero default. Human review remains pending.
