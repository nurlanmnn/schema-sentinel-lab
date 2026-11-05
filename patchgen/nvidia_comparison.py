"""Finite 2-model x 2-prompt development comparison; no repairs or auto-merge."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
from patchgen.nvidia_client import MODELS, credential
from patchgen.live_suite import CASES, ADDITIONAL_CASES

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--model', choices=MODELS, action='append')
    parser.add_argument('--strategy', choices=('candidate_edits','candidate_semantic_edits','candidate_blocks','candidate_semantic_blocks'), action='append')
    args = parser.parse_args()
    models = args.model or MODELS[:2]
    strategies = args.strategy or ('candidate_edits', 'candidate_semantic_edits')
    if len(set(models)) != len(models) or len(set(strategies)) != len(strategies):
        parser.error('models and strategies must be distinct')
    credential()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT/'patchgen/evidence'):
        parser.error('comparison output must be inside patchgen/evidence')
    output.mkdir(parents=True, exist_ok=False)
    (output/'runner-source.py').write_bytes(Path(__file__).read_bytes())
    report = dict(status='running', design=f'{len(models)} models x {len(strategies)} prompts x 8 authored migrations',
                  interpretation='development comparison; prompts informed by prior failures; one sample per cell; no held-out generalization claim',
                  automatic_repairs=0, human_approval_required=True, results=[])
    def save():
        (output/'comparison.json').write_text(json.dumps(report, indent=2)+'\n')
    save()
    for model in models:
        for strategy in strategies:
            label = {MODELS[0]: 'ultra', MODELS[1]: 'super35', MODELS[2]: 'gemma31'}[model] + '-' + {'candidate_edits': 'original', 'candidate_semantic_edits': 'semantic', 'candidate_blocks': 'blocks', 'candidate_semantic_blocks': 'semantic-blocks'}[strategy]
            target = output/label
            command = [sys.executable, '-m', 'patchgen.live_suite', '--backend', 'nvidia',
                       '--model', model, '--strategy', strategy, '--full-benchmark', '--output', str(target)]
            started = time.monotonic()
            with (output/(label+'.log')).open('w') as log:
                result = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
            path = target/'summary.json'
            summary = json.loads(path.read_text()) if path.is_file() else {}
            report['results'].append(dict(label=label, model=model, strategy=strategy,
                exit_code=result.returncode, elapsed_seconds=time.monotonic()-started,
                status=summary.get('status', 'runner_failed'),
                passed=summary.get('validated_model_patches'), planned=summary.get('planned_cases'),
                model_requests=summary.get('model_requests')))
            save()
            print(json.dumps(report['results'][-1]), flush=True)
            if summary.get('status') != 'completed':
                report['status'] = 'stopped_provider_or_runner_failure'
                save()
                return 1
    report['status'] = 'completed'
    save()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
