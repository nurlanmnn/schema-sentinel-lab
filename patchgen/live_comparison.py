"""Audit paired live experiments before attributing a change to model or prompt."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
from patchgen.live_suite import CASES

GATE_FUNCTIONS=('validate_output','verify_source','check_patch','load_validation_profile','apply_and_validate')
GATE_METADATA=('validation_profile','oracle_sha256','benchmark_oracle_sha256','local_codegen_sha256',
               'pubsub_harness_sha256','telemetry_oracle_sha256')


def read(path):return json.loads(path.read_text())


def gate_functions(path):
    tree=ast.parse(path.read_text())
    functions={node.name:ast.dump(node,include_attributes=False) for node in tree.body
               if isinstance(node,ast.FunctionDef) and node.name in GATE_FUNCTIONS}
    if set(functions)!=set(GATE_FUNCTIONS):raise ValueError('missing retained validation functions')
    return functions


def suite(root):
    summary=read(root/'summary.json')
    records=summary['results']
    if (summary['status']!='completed' or summary['mode']!='live_model' or len(records)!=len(CASES)
            or {row['case'] for row in records}!=set(CASES) or summary.get('automatic_repairs')!=0):
        raise ValueError('comparison needs completed six-case live suites without automatic repairs')
    models={read(root/case/'run/proposal/model.json')['tag']['digest'] for case in CASES}
    if len(models)!=1:raise ValueError('inconsistent model identities')
    return summary,next(iter(models))


def compare(left,right):
    left,right=Path(left).resolve(),Path(right).resolve()
    a,model_a=suite(left);b,model_b=suite(right)
    issues=[];rows=[]
    for case in CASES:
        roots=[root/case/'run/proposal' for root in (left,right)]
        inputs=[read(root/'input.json') for root in roots]
        reports=[read(root/'report.json') for root in roots]
        if inputs[0]!=inputs[1]:issues.append(case+': generation inputs differ')
        for key in GATE_METADATA:
            if reports[0].get(key)!=reports[1].get(key):issues.append(case+': gate metadata differs: '+key)
        for required in ('validation_profile','oracle_sha256','benchmark_oracle_sha256','local_codegen_sha256'):
            if any(required not in report for report in reports):issues.append(case+': missing gate metadata: '+required)
        if gate_functions(roots[0]/'generator-source.py')!=gate_functions(roots[1]/'generator-source.py'):
            issues.append(case+': host validation functions differ')
        records=[next(row for row in summary['results'] if row['case']==case) for summary in (a,b)]
        rows.append(dict(case=case,left_validated=records[0]['generated_patch_validated'],
                         right_validated=records[1]['generated_patch_validated']))
    model_changed=model_a!=model_b
    prompt_changed=(a['prompt_version'],a['strategy'])!=(b['prompt_version'],b['strategy'])
    if a['options']!=b['options']:issues.append('inference options differ')
    # A version label is insufficient to establish identical model-comparison prompts.
    if not prompt_changed:
        for case in CASES:
            requests=[sorted((root/case/'run/proposal/requests').glob('*/request.json')) for root in (left,right)]
            if len(requests[0])!=len(requests[1]) or not requests[0]:
                issues.append(case+': request coverage differs or is empty');continue
            for x,y in zip(*requests):
                payloads=[read(path) for path in (x,y)]
                for payload in payloads:payload.pop('model',None)
                if payloads[0]!=payloads[1]:issues.append(case+'/'+x.parent.name+': request payload differs beyond model')
    kind=('confounded' if issues or model_changed and prompt_changed else
          'model_comparison' if model_changed else 'prompt_development' if prompt_changed else 'repeat')
    return dict(comparison_kind=kind,issues=issues,left_model_digest=model_a,right_model_digest=model_b,
                left_prompt=a['prompt_version'],right_prompt=b['prompt_version'],rows=rows,
                source_summary_sha256=[hashlib.sha256((root/'summary.json').read_bytes()).hexdigest() for root in (left,right)],
                scope='six in-sample authored cases, one trial per configuration; no general ranking or human acceptance')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--left',type=Path,required=True);parser.add_argument('--right',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists() or any(root.resolve()==args.output.resolve() or root.resolve() in args.output.resolve().parents
                                   for root in (args.left,args.right)):
        raise ValueError('comparison output must be new and outside retained suites')
    result=compare(args.left,args.right)
    args.output.mkdir(parents=True)
    (args.output/'comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
