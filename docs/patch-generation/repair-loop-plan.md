# Bounded repair loop

Status: implemented with synthetic tests (decision 0042). No live repair run
has been made yet.

The proposal's home-run item asks for a repair loop: when a generated patch
fails validation, feed compiler and test output back to the model for a fixed
number of attempts, and report how much that raises the first-pass rate.

## Run it

```sh
.venv/bin/python -m patchgen.live_suite --locked --full-benchmark --output patchgen/evidence/NEW-locked
.venv/bin/python -m patchgen.repair_suite --source patchgen/evidence/NEW-locked --output patchgen/evidence/NEW-repair
```

The first command is a fresh one-shot baseline (24 requests). It is also a
second sample of the earlier 6/8 result. The second command repairs only the
rejected cases. If two cases fail, that is at most 2 × 2 × 3 = 12 more requests.

## Protocol

1. At most two rounds per rejected case, one request per runtime file per round.
   Stop a case when every original validation gate passes.
2. The same model, sampling, source revision, schema, edit contracts, builds and
   independent runtime oracles as the one-shot run.
3. Feedback carries the previous response plus filtered diagnostics only. See
   decision 0042 for exactly what is shared and withheld.
4. The summary reports `first_pass_validated`, `validated_within_rounds` and each
   case's failure stage separately. A repaired pass never counts as first pass.

## Known targets

From the earlier Gemma/3.1 run: `pubsub-utf8` failed C# compilation
(`ByteString` passed where `byte[]` is required), and `inventory-width` returned
extra text after the TypeScript JSON. A fresh baseline may fail different cases.

## Limits

These eight cases informed prompt development, so results are development
evidence, not held-out reliability. Twelve benchmark cases stay outside the live
route. Human approval is required for every patch.
