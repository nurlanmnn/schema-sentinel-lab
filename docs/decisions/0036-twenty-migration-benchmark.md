# 0036. Complete the authored twenty-case migration benchmark

The final five cases test distinct contract changes across the Python,
TypeScript and C# testbed.

| Case | Required behavior | Rollout constraint |
| --- | --- | --- |
| Telemetry tag move | Emit and read speed at wire tag 7, reserve tag 2, and preserve the threshold | Coordinate readers and writers and migrate stored tag-2 payloads |
| Telemetry JSON key | Emit `groundSpeed` while preserving the Protobuf field and wire bytes | Coordinate clients that use the previous JSON key |
| Packed inventory bins | Read both wire formats and emit packed nonempty lists in order | Pinned TypeScript already packs the old field and can emit an empty packed tag. Empty producer byte equality is outside the oracle |
| Inventory destination oneof | Emit at most one nonempty destination and prefer drop zone when both are requested | Incoming test vectors have at most one destination tag. Migrate historical records containing both before adoption |
| Stock state retirement | Reserve the retired name and number. Report historical value 1 as unknown and keep it ineligible | Consumers that use the old state label need coordination |

The detector compares descriptor changes and keeps policy-dependent location
records partial. Each proposal policy is pinned to its source and a trusted
validation profile. The independent oracles exercise both incoming payloads
and producer output. Pre-migration binaries are negative controls.

Run the full suite with the repository command documented in the README.
The results describe the authored testbed, and each review decision remains
with a human. Human timing and live model results use separate denominators.
