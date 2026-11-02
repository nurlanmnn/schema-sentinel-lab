# 0019: Buildable inventory baseline for integer migration

The authored inventory parser snippets are not executable runtime validation.
Add `simulation.inventory.StockItem` with `sku` string field 1 and signed int32
`quantity` field 2, and direct producer/consumer modes (`--inventory`) in Python,
TypeScript and C#. JSON requests and observations represent quantities as
canonical decimal strings; `in_stock` is strictly decoded quantity > 0. The
baseline tests only valid canonical requests inside the int32 range, not general
input validation or malformed wire rejection.

Configure both existing remote Buf generation and the explicit pinned local
alternative with ts-proto `forceLong=string`. This is the adopted policy for future
64-bit fields. No currently shipped binding changed bytes when regenerating the
new int32 schema; no dependency was added. TS uses BigInt only for its predicate,
while its int32 generated field and producer are numbers. Python uses int and C#
uses int.Parse with invariant culture for the baseline.

`testbed/inventory/run.py` independently hand-encodes Protobuf signed varints
including negative sign extension and multibyte string lengths. It imports no
generated bindings or reference answers. It verifies exact producer bytes,
string-valued decoded quantities, stock decisions, subprocess exits and source
hashes. Baseline evidence `inventory-baseline-001` passes eight cases in each
runtime (24 checks), including signed int32 endpoints, Unicode and a long SKU.
`inventory-baseline-build-001.log` retains compilation, testbed tests and the
original Entity relay round trip. The width oracle has sixteen authored cases,
including +/-2^53 neighbors and int64 endpoints, but has not yet established a
validated width migration. Source/hash dirty state is retained honestly.

Next: pin this baseline, compare int32 -> int64, locate known source sites, draft
bounded TS/C# producer edits, and require exact runtime evidence plus portable
human review. A coordinated consumer rollout is required before producers emit
out-of-int32 values; same wire type alone does not establish mixed-version safety.
