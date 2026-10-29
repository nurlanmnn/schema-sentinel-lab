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
    if case=='v2-identifier-bytes':
        probe_dir=root/'testbed/artifacts/v2-probe';probe_dir.mkdir(parents=True,exist_ok=True)
        (probe_dir/'Probe.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net8.0</TargetFramework><ImplicitUsings>enable</ImplicitUsings></PropertyGroup><ItemGroup><ProjectReference Include="../../../runtimes/csharp/CsharpApp.csproj" /></ItemGroup></Project>')
        (probe_dir/'Program.cs').write_text('''using System.Reflection;
using System.Runtime.CompilerServices;
using Google.Protobuf;
var assembly = Assembly.Load("CsharpApp");
var method = assembly.GetType("Program")!.GetMethods(BindingFlags.NonPublic | BindingFlags.Static).Single(m => m.Name.Contains("ProcessEntity"));
var result = (ITuple)method.Invoke(null, new object[] { Convert.FromHexString(args[0]), "v2" })!;
Console.WriteLine(Convert.ToHexString(((IMessage)result[0]!).ToByteArray()));
''')
        subprocess.run(['dotnet','build',str(probe_dir/'Probe.csproj'),'-c','Release'],cwd=root,check=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
        for text in TEXTS:
            raw=V2(entity_id=text.encode('utf-8')).SerializeToString()
            probe='const {processEntity}=require("./runtimes/typescript/dist/runtimes/typescript/main.js"); const {Entity}=require("./runtimes/typescript/dist/generated/ts/v2/entity.js"); const r=processEntity(Buffer.from("'+raw.hex()+'","hex"),"v2"); console.log(Buffer.from(Entity.encode(r.entity).finish()).toString("hex"));'
            for name,cmd in [('typescript',['node','-e',probe]),('csharp',['dotnet',str(probe_dir/'bin/Release/net8.0/Probe.dll'),raw.hex()])]:
                result=subprocess.run(cmd,cwd=root,text=True,capture_output=True,check=True,timeout=30)
                lines=result.stdout.splitlines()
                assert json.loads(lines[-2])==dict(runtime=name,version='v2',fields={'entity_id':text})
                assert V2.FromString(bytes.fromhex(lines[-1])).entity_id==text.encode('utf-8')
        print('PASS independent: 4 UTF-8 v2 payloads decoded and reencoded in Python, TypeScript and C#')
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
