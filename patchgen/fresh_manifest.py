"""Explicitly seal or verify fresh screening inputs. Authoring never seals implicitly."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from patchgen.fresh_cases import PROFILES, ROOT, fixture

DEFAULT = ROOT/'fresh-screen/manifest.json'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_file(root, path):
    target = root/path
    # Reject symlink directories as well as files, and never hash sensitive output trees.
    if (not target.is_file() or any(part.is_symlink() for part in (target,*target.parents))
            or not target.resolve().is_relative_to(root.resolve())
            or target.name == 'summary.md' or 'raw-response' in target.name):
        raise ValueError('unsafe or missing fresh manifest dependency: '+path)
    return target.read_bytes()


# Modules imported by the fresh detector/locator/adapter, live generation, validation,
# review and manifest routes. Unrelated deterministic recipes and analysis tools are excluded.
ROUTE_MODULES = (
    '__init__', 'adapter', 'anchor_edits', 'binding_analysis', 'detector', 'feedback_blocks',
    'fresh_attempts', 'fresh_cases', 'fresh_manifest', 'fresh_oracle', 'generator', 'live_suite',
    'locator', 'nvidia_client', 'openrouter_client', 'pipeline', 'python_bindings', 'review',
    'request_failures', 'runtime_inventory', 'source_spellings', 'typescript_bindings',
)


def rendered_inputs(root, requests):
    """Rebuild pipeline inputs and exact ordered per-file prompt messages, offline.

    The temporary repository shares pinned objects but checks out only proto/runtime
    sources. No worktree metadata, output artifacts or model credentials are touched.
    """
    from patchgen.anchor_edits import make_prompt
    from patchgen.detector import detect
    from patchgen.fresh_cases import prepare
    from patchgen.locator import locate
    result = {}
    with tempfile.TemporaryDirectory(prefix='fresh-prompt-manifest-') as temporary:
        for revision in sorted({r['source_revision'] for r in requests}):
            source = Path(temporary)/revision
            subprocess.run(['git', 'clone', '--shared', '--no-checkout', '--quiet', str(root), str(source)], check=True)
            subprocess.run(['git', 'update-ref', 'HEAD', revision], cwd=source, check=True)
            subprocess.run(['git', 'checkout', revision, '--', 'runtimes', 'proto'], cwd=source, check=True)
            for request in requests:
                if request['source_revision'] != revision:
                    continue
                change = request['change']
                detector = detect(change['old_schema'], change['new_schema'], change['schema_path'],
                                  revision, change['id'], request['intended_behavior'])
                prepared, _ = prepare(source, detector, locate(source, detector))
                # Match generator.request_model's prompt.json SHA-256 byte convention.
                messages = {file['path']: digest(json.dumps(make_prompt(prepared, file, semantic=True)[0]).encode())
                            for file in prepared['affected_files']}
                result[change['id']] = dict(prepared_input_sha256=digest(json.dumps(prepared, sort_keys=True).encode()),
                    rendered_prompt_sha256={'candidate_semantic_blocks': messages})
    return result


def snapshot(root=ROOT):
    """Compute the complete inventory; verify compares membership as well as digests."""
    from patchgen.live_suite import FRESH_CASES, prompt_fingerprints
    from run_demo import CASES as DEMOS
    if tuple(FRESH_CASES) != PROFILES:
        raise ValueError('fresh suite membership differs from authored cases')
    files, cases = {}, []
    rendered = rendered_inputs(root, [fixture(name, root) for name in FRESH_CASES])
    baseline_roots = ('runtimes/','proto/','generated/','testbed/')
    baseline_names = ('run_local.py','buf.yaml','buf.gen.yaml','buf.lock')
    for name in FRESH_CASES:
        if DEMOS[name] != (name, 'deterministic_fresh'):
            raise ValueError('fresh demo wiring differs from authored case')
        request = fixture(name,root)
        revision = request['source_revision']
        baseline = {}
        paths = subprocess.check_output(['git','ls-tree','-r','--name-only',revision,'--','runtimes','proto','generated','testbed',*baseline_names],cwd=root,text=True).splitlines()
        for path in paths:
            if path.startswith(baseline_roots) or path in baseline_names:
                # These are baseline source/configuration roots, never model evidence roots.
                if Path(path).name == 'summary.md' or 'raw-response' in Path(path).name:
                    raise ValueError('unexpected output artifact in baseline dependency tree')
                baseline[path] = digest(subprocess.check_output(['git','show',revision+':'+path],cwd=root))
                files[path] = digest(read_file(root,path))
        if not baseline:
            raise ValueError('missing pinned baseline sources')
        for directory in (root/'patchgen/fixtures'/name,root/'patchgen/reference'/name):
            for path in sorted(directory.rglob('*')):
                if path.is_symlink():
                    raise ValueError('symlink in fresh inputs')
                if path.is_file():
                    relative = str(path.relative_to(root))
                    files[relative] = digest(read_file(root,relative))
        wrong = json.loads((root/'patchgen/reference'/name/'wrong-patches.json').read_text())
        if len(wrong) < 3 or len({row['patch'] for row in wrong}) != len(wrong):
            raise ValueError('fresh case needs at least three distinct wrong patches')
        if any(Path(row['patch']).name != row['patch'] or not row['patch'].endswith('.patch') for row in wrong):
            raise ValueError('wrong patch entries must be local patch filenames')
        contents = {read_file(root,'patchgen/reference/'+name+'/'+row['patch']) for row in wrong if row.get('reason')}
        if read_file(root,'patchgen/reference/'+name+'/expected.patch') in contents:
            raise ValueError('wrong patch duplicates the reference patch')
        if len(contents) != len(wrong):
            raise ValueError('wrong patches must be distinct with stated reasons')
        cases.append(dict(case=name,profile=name,source_revision=revision,baseline_sha256=baseline, **rendered[name]))
    # Freeze execution code too, so an unchanged fixture cannot silently select a new check.
    harness = ['patchgen/'+name+'.py' for name in ROUTE_MODULES]
    harness += ['patchgen/pipeline-requirements.txt','run_demo.py','run_benchmark.py','run_local.py','tools/codegen/generate.py','tools/codegen/package.json',
                'tools/codegen/package-lock.json','docs/patch-generation/fresh-cases.md']
    harness += [str(p.relative_to(root)) for p in sorted((root/'patchgen/tests').glob('test_fresh*.py'))]
    for path in harness:
        files[path] = digest(read_file(root,path))
    return dict(manifest_version='1.0',split='fresh_screen',cases=cases,files=dict(sorted(files.items())),
                prompt_fingerprints=prompt_fingerprints())


def seal(path=DEFAULT, root=ROOT):
    value = snapshot(root)
    path = Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x') as out:
        out.write(json.dumps(value,indent=2,sort_keys=True)+'\n')
    return value


def verify(path=DEFAULT, root=ROOT):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('fresh cases are unsealed: run fresh_manifest seal only after review')
    value = json.loads(path.read_text())
    current = snapshot(root)
    if value != current:
        changed = sorted(key for key in set(value.get('files',{})) | set(current['files'])
                         if value.get('files',{}).get(key) != current['files'].get(key))
        raise ValueError('fresh manifest mismatch; refuse model run'+(': '+', '.join(changed[:8]) if changed else ' (membership, baseline or prompt fingerprints)'))
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('seal','verify'))
    args = parser.parse_args()
    try:
        value = seal() if args.action == 'seal' else verify()
        print(f"{args.action}: {len(value['cases'])} fresh_screen cases")
        return 0
    except (OSError,ValueError,KeyError,subprocess.SubprocessError) as error:
        print(str(error))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
