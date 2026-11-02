"""Host observations around one fixed authorized suite; not a memory-fit guarantee."""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
command=[sys.executable,'-m','patchgen.live_suite','--model','ministral-3:14b',
         '--output','patchgen/evidence/live-six-ministral14b-001']
start=time.monotonic()
report=dict(status='running',command=command,started_utc=datetime.now(timezone.utc).isoformat(),
            scope='read-only host samples every ten seconds, including preexisting swap; not isolated model RSS or guaranteed peak')
(HERE/'observer.json').write_text(json.dumps(report,indent=2)+'\n')
with (ROOT/'patchgen/evidence/live-six-ministral14b-001.log').open('w') as log:
    process=subprocess.Popen(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
    report['suite_pid']=process.pid
    (HERE/'observer.json').write_text(json.dumps(report,indent=2)+'\n')
    while True:
        sample=dict(elapsed_seconds=time.monotonic()-start,timestamp_utc=datetime.now(timezone.utc).isoformat())
        for name,args in {'memory_pressure':['memory_pressure','-Q'],'swap':['sysctl','vm.swapusage'],'vm_stat':['vm_stat']}.items():
            result=subprocess.run(args,capture_output=True,text=True,timeout=10)
            sample[name]=dict(exit_code=result.returncode,stdout=result.stdout,stderr=result.stderr)
        with (HERE/'samples.jsonl').open('a') as observations:observations.write(json.dumps(sample)+'\n')
        code=process.poll()
        if code is not None:break
        time.sleep(10)
report.update(status='completed',suite_exit_code=code,elapsed_seconds=time.monotonic()-start)
(HERE/'observer.json').write_text(json.dumps(report,indent=2)+'\n')
raise SystemExit(code)
