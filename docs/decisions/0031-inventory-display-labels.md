# 0031. Collapse inventory display labels to one value

This pinned migration changes repeated `StockItem.display_labels` to a
singular string at field 4. Runtime producers keep accepting a JSON array and
serialize the last label. An empty array or a last label of the empty string
maps to the proto3 default and emits no label tag. Consumers observe a scalar
when the request opts into label observations. Stock eligibility and the
quantity representation stay the same.

The detector classifies a repeated proto3 string becoming an implicit singular
string when its other descriptor metadata matches exactly. The locator reports
syntax candidates. The pinned strategy requires its authored construction and
observation sites. The generic inventory collection policies still
need separate evidence before generation.

The independent oracle exercises missing, duplicate, multilingual, long and
empty trailing labels. It uses different producer input lists and older
repeated consumer payloads, and checks stock eligibility and exact wire bytes
across Python, TypeScript and C#.

A singular reader consumes the last occurrence from an older repeated payload.
An older reader sees at most a one-element list from a new producer. Earlier
labels disappear after collapse, and a singular JSON observation changes the
application contract. Coordinate the rollout before relying on that shape.
Human review remains pending.
