# 0026: Explicit tracked-runtime inventory

November 3, 2026. Strengthens deterministic scan completeness under decision 0024.

The locator inventories all Git entries below `runtimes/` at the exact source
revision with NUL-delimited `git ls-tree`, preserving Unicode names and detecting
unsupported whitespace paths. Each row records path, Git mode, object type,
object ID and disposition. Only regular/executable `.py`, `.ts` and `.cs` blobs
are scanned. Symlinks and gitlinks are never interpreted as source contents.

A narrow auxiliary policy recognizes the repository's dependency/build inputs:
`requirements.txt`, `package.json`, `package-lock.json`, `tsconfig.json` and
`.csproj` files. These are inventoried, not analyzed as runtime code. Unknown
extensions, extensionless files and all other entries block completeness. Adding
an auxiliary class requires an explicit policy update, not a silent skip. This
policy does not claim that auxiliary files cannot affect execution.

New locator records use scan manifest version 1.1 and include the complete tree
inventory alongside supported-source hashes. The adapter recomputes both,
rejecting omitted/altered inventory rows and any unsupported entry even if the
producer forges `status: complete`. Version 1.0 source manifests remain readable
but are also checked for unsafe/unsupported runtime entries. Supplied legacy
records without a manifest retain explicitly narrower provenance.

This closes missing-file and Git-mode blind spots; it does not establish receiver
identity, discover code outside `runtimes/`, or prove whole-program completeness.
No dependency was added. The shared `runtime_inventory` module owns the language
and auxiliary policy used by locator and adapter, replacing their duplicated
language tables.
