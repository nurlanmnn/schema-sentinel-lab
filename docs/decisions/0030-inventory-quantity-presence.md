# 0030. Preserve explicit inventory quantity presence

The pinned migration makes `StockItem.quantity` an optional int32 at its
existing field number. Producers omit the quantity for JSON null and
serialize an explicit field for zero. Consumers observe absent quantity as
JSON null and present quantities as decimal strings. Stock eligibility
still requires a positive quantity and unspecified stock state.

The detector recognizes an otherwise identical scalar field that gains one
trailing, single-member synthetic oneof without options. Existing group
comparison and unrelated descriptor checks still apply. The pinned proposal
uses the existing locator and requires its authored producer and consumer
sites. Generic generation stays gated.

The independent oracle uses distinct producer inputs and consumer payloads.
It checks absent, zero, signed values and int32 boundaries, with unspecified,
quarantined and unknown stock states. It verifies exact produced wire bytes,
consumer JSON and eligibility across Python, TypeScript and C#.

Field numbers and wire types remain compatible. Old writers omit zero and
old readers observe both absent and explicit zero as zero. Coordinate the
upgrade when preserving the distinction matters, especially across older
decode and re-encode steps. Human review remains pending.
