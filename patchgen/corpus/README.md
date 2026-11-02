# Authored domain corpus

These eight small scenarios broaden **detector and locator evaluation** beyond
the existing Entity testbed. They do not have generated patches, generated bindings,
compilation/runtime oracles, a manual timing baseline or human acceptance. They
do not satisfy the twenty-case end-to-end migration benchmark milestone.

The fixtures are original public examples of vehicle telemetry, stock inventory
and orders. No controlled standards or external system source is used. Consumer
snippets intentionally show construction, observation and a business predicate
in each language. They are parser inputs, not standalone applications.

`cases.json` records independently authored intent, structural status/category
expectations and manual line inventories. The runner receives only schemas,
source revision and behavior when producing detector/locator output. Expectations
are consulted after those records are written. SHA-1 Git seeds use fixed metadata
and exact source bytes; source/content hashes are retained in production records.

| Scenario | Current detector | Current locator | Unresolved migration requirement |
| --- | --- | --- | --- |
| Ground-speed rename | field_renamed | 9 known lines | Preserve units and threshold; change observation key |
| Speed float to double | field_type_changed | 9 known lines | Coordinate incompatible wire-type rollout |
| Speed units m/s to km/h | partial, no structural event | blocked | Scale values and threshold; semantics are not inferred |
| Stock quantity int32 to int64 | field_type_changed | 9 known lines | Exact large integers, including TypeScript representation |
| Label list to scalar | partial | blocked | Cardinality and first-label policy |
| Add active BACKORDERED enum value | enum_value_added | partial, unsupported | Analyze active state predicates and enum consumers |
| Remove order currency | field_removed | 9 known lines | Explicit USD-only policy and predicate migration |
| Amount gains optional presence | partial | blocked | Preserve absence versus explicit zero |

The supported locator rows contain 36 known lines across four scenarios and
three domains. Two scenarios use the same telemetry sites. Recovery of these
lines is a small authored-fixture result, not general impact completeness.
Receiver identity and indirect uses remain outside the locator's proof.

Run from the Lab root after installing `patchgen/pipeline-requirements.txt`:

```sh
.venv/bin/python -m patchgen.corpus --output patchgen/evidence/my-domain-corpus
```

The output must be new. Each scenario retains its reproducible source seed,
detector, locator, optional adapter records, measurements and result. Partial
outcomes are recorded individually and later cases still run. The exit status
only checks agreement with the declared expectations, including known unsupported
boundaries. `generated_validated_migrations` remains zero. An expected rejection
is a visible limitation, not a migration success.
