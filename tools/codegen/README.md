# Pinned local generation

The default `buf generate` uses the public Buf remote plugins. A retained
telemetry build hit its remote request quota. This optional local path uses
protoc **25.1** and ts-proto **1.165.0**, the existing remote configuration's
versions. It asks the installed Buf compiler for normalized descriptors, then
invokes the local plugins. It does not silently fall back after a failed run.
The six existing Entity binding files were byte-identical after local generation.
This is a tested macOS ARM64 setup, not a cross-platform installer.

From the repository root:

```sh
mkdir -p .tools/protoc-25.1
curl -fL https://github.com/protocolbuffers/protobuf/releases/download/v25.1/protoc-25.1-osx-aarch_64.zip -o .tools/protoc-25.1.zip
# Check before extracting: SHA-256
# 320308ce18c359564948754f51748de41cf02a4e7edf0cf47a805b9d38610f16
shasum -a 256 .tools/protoc-25.1.zip
unzip .tools/protoc-25.1.zip -d .tools/protoc-25.1
npm ci --prefix tools/codegen
python3 tools/codegen/generate.py --root .
```

The downloaded compiler and installed npm packages are ignored. The npm lock
pins transitive versions and integrity. Generation does not install or download
tools. Proposal source cannot select executables, generation options or checks.

License records: `docs/licenses/codegen/`. Protobuf's pinned source LICENSE is
BSD-3-Clause. ts-proto's pinned repository LICENSE is Apache-2.0; its package
metadata declares ISC, as does ts-proto-descriptors (same upstream repository,
no LICENSE shipped in that package). Both manifest declarations and upstream
license texts are retained, rather than silently treating them as identical.
The inventory retains transitive package metadata and shipped notices. These
are permissive licenses compatible with the project's open-source direction;
this records engineering due diligence, not a legal certification.

Sources: [Protobuf v25.1 LICENSE](https://github.com/protocolbuffers/protobuf/blob/v25.1/LICENSE),
[ts-proto v1.165.0 LICENSE](https://github.com/stephenh/ts-proto/blob/v1.165.0/LICENSE).

The remote and local paths use `forceLong=string` for future Protobuf 64-bit
integer fields. This keeps generated TypeScript values exact across JavaScript's
safe-integer boundary. The inventory JSON contract also uses decimal strings.
Int32 fields keep their generated number representation. Existing Entity and
telemetry generated files are byte-identical under this option.
