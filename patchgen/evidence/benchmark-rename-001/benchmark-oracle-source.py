"""Independent benchmark checks; reference values never enter model requests."""
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import urllib.request

RUNTIMES = ['python','typescript','csharp']
TEXTS = ['normal-001','','entity-雪-🚀','quotes "\n\\']


def main(workspace, case):
    root=Path(workspace).resolve()
    sys.path.insert(0,str(root/'generated/python'))
    from v1.entity_pb2 import Entity
    from v2.entity_pb2 import Entity as V2
    field='display_name' if case=='entity-name-rename' else 'name'
    assert list(Entity.DESCRIPTOR.fields_by_name)==['entity_id',field]
    assert V2.DESCRIPTOR.fields_by_name['entity_id'].type == (12 if case=='v2-identifier-bytes' else 9)
    if case=='unused-enum-addition':
        from v1.entity_pb2 import Status
        assert Status.items()==[('STATUS_UNSPECIFIED',0),('STATUS_ACTIVE',1),('STATUS_SUSPENDED',2)]
    # Exercise actual migrated Python processor plus standalone TS/C# for v1 and v2.
    spec=importlib.util.spec_from_file_location('runtime',root/'runtimes/python/main.py')
    runtime=importlib.util.module_from_spec(spec);spec.loader.exec_module(runtime)
    for text in TEXTS:
        v2=V2(entity_id=text.encode('utf-8') if case=='v2-identifier-bytes' else text)
        decoded,fields=runtime.process_entity(v2.SerializeToString(),'v2')
        assert fields=={'entity_id':text}
        assert decoded.SerializeToString()==v2.SerializeToString()
    try:runtime.process_entity(b'','invalid')
    except ValueError:pass
    else:raise AssertionError('invalid version accepted')
    for version in ('v1','v2'):
        commands=[([sys.executable,'runtimes/python/main.py','--version',version],'python','py_101','Sensor A'),
                  (['node','runtimes/typescript/dist/runtimes/typescript/main.js']+(['--v2'] if version=='v2' else []),'typescript','ts_303','Sensor C'),
                  (['dotnet','runtimes/csharp/bin/Release/net8.0/CsharpApp.dll']+(['--v2'] if version=='v2' else []),'csharp','cs_202','Sensor B')]
        for cmd,name,identifier,sample in commands:
            result=subprocess.run(cmd,cwd=root,capture_output=True,text=True,check=True,timeout=30)
            record=json.loads(result.stdout.splitlines()[-1]);expected={'entity_id':identifier}
            if version=='v1':expected[field]=sample
            assert record==dict(runtime=name,version=version,fields=expected),record
    # For bytes v2, drive TS and C# exported/isolated processors with all text cases.
    # C# ProcessEntity is local; create an evaluator copy with only its standalone branch replaced.
    if case=='v2-identifier-bytes':
        for text in TEXTS:
            probe='const {processEntity}=require("./runtimes/typescript/dist/runtimes/typescript/main.js"); const {Entity}=require("./runtimes/typescript/dist/generated/ts/v2/entity.js"); processEntity(Entity.encode({entityId:new TextEncoder().encode('+json.dumps(text)+')}).finish(),"v2");'
            result=subprocess.run(['node','-e',probe],cwd=root,text=True,capture_output=True,check=True,timeout=30)
            assert json.loads(result.stdout.splitlines()[-1])['fields']=={'entity_id':text}
        # Cross-runtime v2 conformance needs C# arbitrary payload access; do not claim it from samples.
    spec=importlib.util.spec_from_file_location('runner',root/'testbed/scripts/run-local.py')
    runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
    process=subprocess.Popen([sys.executable,str(root/'testbed/scripts/run-local.py'),'--serve'],cwd=root,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    try:
        for port in (8002,8001,8000):
            for _ in range(150):
                if process.poll() is not None:raise AssertionError(process.stdout.read())
                try:
                    with urllib.request.urlopen(f'http://127.0.0.1:{port}/health',timeout=1):break
                except OSError:time.sleep(.2)
            else:raise AssertionError('services not ready')
        for text in TEXTS:
            expected={'entity_id':text,field:text}
            raw=Entity(**expected).SerializeToString()
            req=urllib.request.Request('http://127.0.0.1:8000/relay',data=raw,headers={'Content-Type':'application/x-protobuf'})
            with urllib.request.urlopen(req,timeout=15) as response:
                decoded=Entity.FromString(response.read())
                observations=json.loads(response.headers['X-Schema-Sentinel-Observations'])
                trace=json.loads(response.headers['X-Service-Trace'])
            assert {f.name:getattr(decoded,f.name) for f in decoded.DESCRIPTOR.fields}==expected
            assert observations==[dict(runtime=r,fields=expected) for r in RUNTIMES]
            assert trace==RUNTIMES
        print('PASS independent: 4 v1 payloads through three services, 6 standalone samples, v2 Python text cases and invalid version')
    finally:
        if process.poll() is None:
            process.send_signal(signal.SIGINT)
            try:process.wait(timeout=15)
            except subprocess.TimeoutExpired:runner.stop_processes([process])
        print(process.stdout.read())


if __name__=='__main__':main(*sys.argv[1:])
