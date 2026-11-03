"""Finish authorized evidence collection and unload the model without further agent work."""
import json
from pathlib import Path
import subprocess
import sys
import time
from patchgen.generator import api

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
source=ROOT/'patchgen/evidence/live-six-ministral14b-001'
report=dict(status='waiting_for_completed_suite',scope='analysis and cleanup only; no repair, approval, apply, merge or extra model requests')
def save():(HERE/'finalizer.json').write_text(json.dumps(report,indent=2)+'\n')
save()
deadline=time.monotonic()+7200
while True:
    try:summary=json.loads((source/'summary.json').read_text())
    except (OSError,ValueError):summary={}
    if summary.get('status')=='completed':break
    if time.monotonic()>deadline:
        report.update(status='timed_out',error='Suite still incomplete; retained evidence unchanged. No final rate computed.')
        save();raise SystemExit(1)
    time.sleep(10)
commands=[['-m','patchgen.live_analysis','--source',str(source),'--output',str(ROOT/'patchgen/evidence/live-six-ministral14b-analysis001')],
          ['-m','patchgen.live_comparison','--left',str(ROOT/'patchgen/evidence/live-six-ministral8b-001'),'--right',str(source),
           '--output',str(ROOT/'patchgen/evidence/live-8b-14b-comparison001')]]
report['analysis_exit_codes']=[]
try:
    for index,command in enumerate(commands,1):
        with (HERE/f'finalizer-command-{index:02d}.log').open('w') as log:
            code=subprocess.run([sys.executable,*command],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT).returncode
        report['analysis_exit_codes'].append(code)
    report.update(status='completed',validated_model_patches=summary['validated_model_patches'],planned_cases=summary['planned_cases'],
                  actual_model_requests=summary['model_requests'],human_approval_required=True)
finally:
    try:
        report['unload']=api('http://127.0.0.1:11434','/api/generate',{'model':'ministral-3:14b','keep_alive':0})
        time.sleep(2)
        report['models_after']=api('http://127.0.0.1:11434','/api/ps')
    except (OSError,ValueError) as error:report['cleanup_error']=str(error)
    save()
