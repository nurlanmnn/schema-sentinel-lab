"""Run three bounded live cases sequentially, retaining every failure."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from patchgen.generator import command,save,ContractError

ROOT=Path(__file__).resolve().parents[1]


def prepare_enum_seed(repo=ROOT):
    seed=json.loads((ROOT/'patchgen/fixtures/benchmark-seed.json').read_text())
    # Recreate the exact source object on a fresh clone; never retarget fixtures.
    with tempfile.TemporaryDirectory() as tmp:
        env=dict(os.environ,GIT_INDEX_FILE=str(Path(tmp)/'index'))
        def git(args,text=None):
            return subprocess.check_output(['git',*args],cwd=repo,env=env,text=True,input=text).strip()
        git(['read-tree',seed['base_revision']])
        blob=git(['hash-object','-w','--stdin'],seed['enum_seed_schema'])
        git(['update-index','--cacheinfo',f'100644,{blob},proto/v1/entity.proto'])
        tree=git(['write-tree'])
        env.update(GIT_AUTHOR_NAME='Schema Sentinel benchmark',GIT_AUTHOR_EMAIL='benchmark@example.invalid',GIT_COMMITTER_NAME='Schema Sentinel benchmark',GIT_COMMITTER_EMAIL='benchmark@example.invalid',GIT_AUTHOR_DATE='2026-10-28T12:00:00Z',GIT_COMMITTER_DATE='2026-10-28T12:00:00Z')
        revision=git(['commit-tree',tree,'-p',seed['base_revision']],seed['enum_seed_commit_message'])
    if revision!=seed['enum_seed_revision']:raise ContractError('enum seed revision mismatch')
    return seed


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--references',action='store_true',help='offline reference patches instead of live model; never counted as model success');args=parser.parse_args()
    output=args.output.resolve();output.mkdir(parents=True,exist_ok=False)
    seed=prepare_enum_seed();results=[]
    for name in seed['cases']:
        target=output/name
        cmd=[sys.executable,'-m','patchgen.generator','--prepare-source','--strategy','migration_edits','--model','ministral-3:8b','--fixture',str(ROOT/'patchgen/fixtures'/name/'runtime-input.json'),'--output',str(target),'--validate']
        if name=='entity-name-rename':cmd+=['--validation-profile',name]
        if args.references:
            reference=ROOT/'patchgen/reference'/name/'response.json'
            if not reference.exists():
                results.append(dict(case=name,status='not_run',reason='no offline reference response; additive case is live-only'));continue
            cmd+=['--response',str(reference)]
        with (output/(name+'.log')).open('w') as log:
            result=subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        report=json.loads((target/'report.json').read_text())
        results.append(dict(case=name,exit_code=result.returncode,**report))
        print(name+': '+report['status'],flush=True)
    save(output/'summary.json',dict(benchmark_seed_version='1.0',mode='offline_references' if args.references else 'live_model',results=results,human_approval_required=True,scope='three new seed cases; not the 20-case benchmark; sequential shared-port validation'))
    return 1 if any(r['status']=='failed' for r in results) else 0


if __name__=='__main__':raise SystemExit(main())
