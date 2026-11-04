# 0028: Inventory ZigZag wire migration

The eighth buildable benchmark migration changes `StockItem.quantity` from
`int32` to `sint32` at field 2. It keeps the signed int32 range, canonical
decimal-string JSON and the strict positive stock predicate. The proposal
validates the existing runtime source shapes and changes the schema only.
Pinned code generation supplies the revised codecs.

The old and new bytes have different meanings even though both types use the
varint wire category. Producers and consumers need a coordinated rollout.
Persisted old payloads require decoding with the old schema and re-encoding.
The case checks valid canonical input strings, endpoints, zero, and signed
varint-size boundaries. The oracle computes bytes independently and compares
decoded quantities, stock decisions and produced bytes in all three runtimes.

Run `.venv/bin/python run_demo.py --case inventory-zigzag --local-codegen --output
/path/to/new-output` from the prepared Lab checkout. The profile binds the
source commit, new schema and independent oracle mode. The portable review
checks the retained oracle evidence. Approval remains a separate human decision.

The passing demo retained 48 runtime checks. A compiled legacy signed-varint
codec from the int64 width migration failed the ZigZag oracle at the first
nonzero quantity. The chosen negative values are within the original int32
range, where the legacy int32 and int64 encodings agree. This control demonstrates
the wrong wire policy on that overlap. See `patchgen/evidence/eight-migration-suite-001`.
