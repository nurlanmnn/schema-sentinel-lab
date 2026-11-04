# 0034. Rename the inventory hold state without changing its number

The pinned migration changes the enum symbol for stock state 1 from
`STOCK_STATE_QUARANTINED` to `STOCK_STATE_ON_HOLD`. The three runtimes
emit `ON_HOLD` when the caller opts into symbolic state observations.
Unknown numbers still produce `UNKNOWN`, positive unspecified stock
stays eligible, and held stock stays blocked. Producer defaults and
the decimal quantity contract remain the same.

The detector accepts one nondefault proto3 enum symbol rename when
the ordered numeric values and all descriptor metadata remain stable.
Aliases, changes to the zero symbol, and metadata changes stay outside
that boundary. The enum locator still reports candidates. The pinned
policy requires its authored symbol and label edit sites.

The independent oracle submits numeric payloads and checks the canonical
labels, opt-in behavior, eligibility, and producer bytes across Python,
TypeScript, and C#. Old numeric wire payloads remain readable. Application
clients that consume symbolic strings need to handle the new name.
Human review remains pending.
