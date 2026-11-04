# 0029. Add a pinned stock release enum migration

Inventory consumers treat positive quantity as eligible when the stock state
is unspecified. Quarantined and unrecognized states fail closed. The ninth
authored migration adds `STOCK_STATE_RELEASED = 2` and extends that allow-list
while preserving producer defaults and decimal-string quantity observations.

The generic enum scan remains partial. The explicit stock-release strategy
requires the pinned source, the exact descriptor event and the written policy.
It checks its expected consumer edits against the syntax candidates and
leaves the other candidates untouched. Other enum additions still stop at
the existing analysis boundary.

The independent oracle crosses unspecified, quarantined, released and
unknown enum values with negative, zero, one and maximum int32 quantities.
It builds payload bytes independently of generated bindings and checks all
48 runtime outcomes, including legacy default producer bytes. The compiled
pre-migration runtime fails on a positive released item.

Deploy consumers before emitting the released state when consistent
eligibility matters. Older consumers block released stock. The benchmark
covers these authored state and quantity combinations. Review remains pending.
