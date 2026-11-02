"""Explicit local alternative to remote Buf generation, pinned to existing versions.

Install protoc 25.1 at .tools/protoc-25.1 and npm ci --prefix tools/codegen.
Tool paths are owned by the implementation checkout, never by a proposed patch.
"""
import argparse
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def generate(workspace, tools_root=ROOT):
    workspace = workspace.resolve()
    protoc = tools_root/'.tools/protoc-25.1/bin/protoc'
    plugin = tools_root/'tools/codegen/node_modules/.bin/protoc-gen-ts_proto'
    if not protoc.is_file() or not plugin.is_file():
        raise RuntimeError('Missing pinned local codegen tools; see tools/codegen/README.md')
    version = subprocess.check_output([str(protoc), '--version'],text=True).strip()
    if version != 'libprotoc 25.1':
        raise RuntimeError('Local generation requires protoc 25.1')
    import json
    package = tools_root/'tools/codegen/node_modules/ts-proto/package.json'
    if json.loads(package.read_text())['version'] != '1.165.0':
        raise RuntimeError('Local generation requires ts-proto 1.165.0')
    for language in ('python','csharp','ts'):
        (workspace/'generated'/language).mkdir(parents=True,exist_ok=True)
    files = sorted(str(p.relative_to(workspace/'proto')) for p in (workspace/'proto').rglob('*.proto'))
    # Match Buf's normalized descriptors, including explicit default json_name.
    with tempfile.TemporaryDirectory(prefix='schema-sentinel-codegen-') as temporary:
        descriptor = Path(temporary)/'schema.binpb'
        subprocess.run(['buf', 'build', '--as-file-descriptor-set', '-o', str(descriptor)],
                       cwd=workspace,check=True)
        subprocess.run([str(protoc), '--descriptor_set_in='+str(descriptor), '--python_out=generated/python',
                        '--csharp_out=generated/csharp', '--csharp_opt=base_namespace=Simulation',
                        '--plugin=protoc-gen-ts_proto='+str(plugin), '--ts_proto_out=generated/ts', *files],
                       cwd=workspace,check=True)
    return dict(protoc_version=version, ts_proto_version='1.165.0',
                buf_version=subprocess.check_output(['buf','--version'],text=True).strip(),
                sha256={name:hashlib.sha256(path.read_bytes()).hexdigest() for name,path in {
                    'protoc':protoc, 'ts-proto-plugin':plugin.resolve(),
                    'ts-proto-build':tools_root/'tools/codegen/node_modules/ts-proto/build/plugin.js',
                    'package-lock.json':tools_root/'tools/codegen/package-lock.json'}.items()})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    args = parser.parse_args()
    try:
        generate(args.root)
    except (OSError,RuntimeError,subprocess.SubprocessError) as error:
        print(str(error),file=sys.stderr)
        raise SystemExit(1)
