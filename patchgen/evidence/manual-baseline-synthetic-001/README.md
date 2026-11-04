# Synthetic manual baseline check

The evaluator at revision `e9be411` applied the existing known-correct
telemetry units patch to the pinned source. Generation, build, unit tests,
round trip and all 24 runtime comparisons passed. The existing wrong-threshold
patch reached the semantic oracle and failed at case 1. The kit manifest
identifies the archive and both participant documents by SHA-256.

These runs used authored controls. No human elapsed time or review decision
was recorded.
