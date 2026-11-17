"""Authored fresh cases must work with real generated bindings in every language.

The unit route applies exactly the patches accepted by generator.apply_and_validate,
then compiles and exercises the retained oracle vectors without package downloads.
Entity decoder tests invoke the same functions used by subscribers, without sockets.
Full pipeline/review integration is separately exercised when loopback is available.
"""
import copy
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from patchgen import fresh_cases, fresh_oracle, generator
from patchgen.detector import detect
from patchgen.locator import locate
from patchgen.review import check_host_evidence
from tools.codegen.generate import generate

ROOT = Path(__file__).resolve().parents[2]


def run(command, cwd, env=None):
    return subprocess.run([str(x) for x in command],cwd=cwd,env=env,capture_output=True,text=True,timeout=180)


def adapted(source, name):
    request = fresh_cases.fixture(name)
    c = request['change']
    detector = detect(c['old_schema'],c['new_schema'],c['schema_path'],request['source_revision'],name,request['intended_behavior'])
    return fresh_cases.prepare(source,detector,locate(source,detector))[0]


class FreshContractTests(unittest.TestCase):
    def test_reference_and_wrong_patches_are_distinct_and_confined(self):
        for name in fresh_cases.PROFILES:
            request = fresh_cases.fixture(name)
            c = request['change']
            result = detect(c['old_schema'],c['new_schema'],c['schema_path'],request['source_revision'],name,request['intended_behavior'])
            self.assertEqual(result['status'],'complete')
            files = [dict(path=p) for p in fresh_cases.EDITS[name]]
            case = dict(change=c,affected_files=files)
            directory = ROOT/'patchgen/reference'/name
            controls = json.loads((directory/'wrong-patches.json').read_text())
            self.assertGreaterEqual(len(controls),3)
            contents = [(directory/row['patch']).read_text() for row in controls]
            self.assertEqual(len(set(contents)),len(contents))
            for content in [(directory/'expected.patch').read_text(),*contents]:
                generator.check_patch(content,case)
                self.assertNotIn('diff --git a/generated/',content)
                self.assertNotIn('diff --git a/testbed/',content)
            self.assertTrue(all(row['reason'] for row in controls))

    def test_profiles_bind_exact_schema_source_and_policy(self):
        for name in fresh_cases.PROFILES:
            request = fresh_cases.fixture(name)
            request['affected_files'] = [dict(path=p) for p in fresh_cases.EDITS[name]]
            profile, diff = generator.load_validation_profile(request,name)
            self.assertEqual(profile['fresh_case'],name)
            self.assertEqual(diff,'')
            for key in ('source_revision','intended_behavior'):
                wrong=copy.deepcopy(request);wrong[key]+='changed'
                with self.assertRaises(generator.ContractError):generator.load_validation_profile(wrong,name)

    def test_json_types_and_presence_are_checked(self):
        for name in fresh_cases.PROFILES[1:]:
            _, expected = fresh_oracle.vectors(name)
            fresh_oracle.check_results(expected,expected)
            wrong=copy.deepcopy(expected)
            key='speeding' if 'speeding' in wrong[0] else 'in_stock'
            wrong[0][key]=int(wrong[0][key])
            with self.assertRaises(ValueError):fresh_oracle.check_results(wrong,expected)
            wrong=copy.deepcopy(expected);wrong[0]['constructed_payload']='AA=='
            with self.assertRaises(ValueError):fresh_oracle.check_results(wrong,expected)

    def test_telemetry_accepts_float32_json_spellings_but_not_other_values_or_types(self):
        import struct
        for name in fresh_cases.PROFILES[1:3]:
            _, expected = fresh_oracle.vectors(name)
            shortest = copy.deepcopy(expected)
            for row in shortest:
                value = row['fields']['speed_mps']
                if value is not None:
                    row['fields']['speed_mps'] = float(format(value, '.8g'))
            fresh_oracle.check_results(shortest, expected)
            fresh_oracle.check_results(expected, expected)
            index = next(i for i, row in enumerate(expected) if row['fields']['speed_mps'] is not None)
            for invalid in ('30.000002', True, False, None, float('nan'), float('inf'), 1e100):
                wrong = copy.deepcopy(expected)
                wrong[index]['fields']['speed_mps'] = invalid
                with self.subTest(case=name, invalid=invalid), self.assertRaises(ValueError):
                    fresh_oracle.check_results(wrong, expected)
            # An adjacent representable float must still be rejected.
            value = expected[index]['fields']['speed_mps']
            bits = struct.unpack('I', struct.pack('f', value))[0]
            wrong = copy.deepcopy(expected)
            wrong[index]['fields']['speed_mps'] = struct.unpack('f', struct.pack('I', bits ^ 1))[0]
            with self.assertRaises(ValueError):
                fresh_oracle.check_results(wrong, expected)

    def test_broker_nulls_are_opt_in_and_field_specific(self):
        from testbed.pubsub.broker import Broker
        for allowed in ((),('name',)):
            broker=Broker(nullable_fields=allowed)
            broker.dispatch('/subscribe',dict(subscriber='python',runtime='python',topics=['entity.v1']))
            broker.dispatch('/publish',dict(topic='entity.v1',payload=''))
            before=broker.state()
            for fields in (dict(entity_id=None),dict(name=0),dict(name=False),dict(name=[])):
                with self.assertRaises(ValueError):broker.dispatch('/ack',dict(subscriber='python',message_id=1,fields=fields))
                self.assertEqual(broker.state(),before)
            if allowed:
                broker.dispatch('/ack',dict(subscriber='python',message_id=1,fields=dict(entity_id='',name=None)))
                self.assertIsNone(broker.state()['acknowledgements'][0]['fields']['name'])
            else:
                with self.assertRaises(ValueError):broker.dispatch('/ack',dict(subscriber='python',message_id=1,fields=dict(name=None)))
                self.assertEqual(broker.state(),before)

    def test_producer_inputs_do_not_echo_consumed_payloads(self):
        for name in fresh_cases.PROFILES[1:]:
            requests, expected = fresh_oracle.vectors(name)
            self.assertTrue(any(r['payload'] != e['constructed_payload'] for r,e in zip(requests,expected)))


class FreshRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary=tempfile.TemporaryDirectory(prefix='fresh-runtime-tests-')
        cls.base=Path(cls.temporary.name)
        cls.source=cls.base/'source'
        cls.revision=fresh_cases.fixture(fresh_cases.PROFILES[0])['source_revision']
        result=run(['git','worktree','add','--detach',cls.source,cls.revision],ROOT)
        if result.returncode:
            cls.temporary.cleanup()
            raise RuntimeError('fresh runtime tests need writable git metadata (use an isolated clone): '+result.stderr)
        cls.env=dict(os.environ,DOTNET_CLI_HOME=str(cls.base/'dotnet-home'),DOTNET_CLI_TELEMETRY_OPTOUT='1',
                     DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1',DOTNET_CLI_WORKLOAD_UPDATE_NOTIFY_DISABLE='true',
                     NUGET_PACKAGES=os.environ.get('NUGET_PACKAGES',str(Path.home()/'.nuget/packages')))
        cls.reflector=cls.base/'decoder'
        cls.reflector.mkdir()
        (cls.reflector/'Decoder.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net8.0</TargetFramework><ImplicitUsings>enable</ImplicitUsings></PropertyGroup></Project>')
        (cls.reflector/'Program.cs').write_text('''using System.Reflection;
using System.Runtime.Loader;
using System.Text.Json;
var directory = Path.GetDirectoryName(Path.GetFullPath(args[0]))!;
AssemblyLoadContext.Default.Resolving += (_, name) => Assembly.LoadFrom(Path.Combine(directory, name.Name + ".dll"));
var assembly = Assembly.LoadFrom(args[0]);
var method = assembly.GetType("Program")!.GetMethods(BindingFlags.Static | BindingFlags.NonPublic).Single(m => m.Name.Contains("g__ProcessEntity"));
using var input = JsonDocument.Parse(Console.In.ReadToEnd());
var protobuf = Assembly.Load("Google.Protobuf");
var encode = protobuf.GetType("Google.Protobuf.MessageExtensions")!.GetMethods().Single(m => m.Name == "ToByteArray" && m.GetParameters().Length == 1);
foreach (var row in input.RootElement.EnumerateArray()) {
    var console = Console.Out;
    object result;
    try {
        Console.SetOut(TextWriter.Null);
        result = method.Invoke(null, new object[] { Convert.FromBase64String(row.GetProperty("payload").GetString()!), row.GetProperty("version").GetString()! })!;
    } finally { Console.SetOut(console); }
    var entity = result.GetType().GetField("Item1")!.GetValue(result);
    var fields = result.GetType().GetField("Item2")!.GetValue(result);
    var wire = (byte[])encode.Invoke(null, new object[] { entity! })!;
    Console.WriteLine(JsonSerializer.Serialize(new { fields, payload = Convert.ToBase64String(wire) }));
}
''')
        result=run(['dotnet','build',cls.reflector/'Decoder.csproj','--configuration','Release','-p:NuGetAudit=false','--ignore-failed-sources'],ROOT,cls.env)
        if result.returncode:raise RuntimeError(result.stdout+result.stderr)

    @classmethod
    def tearDownClass(cls):
        run(['git','worktree','remove','--force',cls.source],ROOT)
        # Child worktrees were removed per subtest; prune metadata after temporary cleanup.
        cls.temporary.cleanup()
        run(['git','worktree','prune'],ROOT)

    def build(self, workspace):
        (workspace/'.venv').symlink_to(ROOT/'.venv',target_is_directory=True)
        (workspace/'runtimes/typescript/node_modules').symlink_to(ROOT/'runtimes/typescript/node_modules',target_is_directory=True)
        generate(workspace)
        commands=[['npm','run','build','--prefix','runtimes/typescript'],
                  ['dotnet','build','runtimes/csharp/CsharpApp.csproj','--configuration','Release',
                   '-p:NuGetAudit=false','--ignore-failed-sources']]
        for command in commands:
            result=run(command,workspace,self.env)
            if result.returncode:return result.stdout+result.stderr
        return None

    def entity_decoders(self, workspace):
        samples=fresh_oracle.entity_samples()
        data=json.dumps([dict(version=row['topic'].removeprefix('entity.'),payload=fresh_oracle.b64(row['payload'])) for row in samples])
        py='''import base64,contextlib,io,json,runpy,sys
module=runpy.run_path('runtimes/python/main.py')
for row in json.load(sys.stdin):
    with contextlib.redirect_stdout(io.StringIO()):
        entity,fields=module['process_entity'](base64.b64decode(row['payload']),row['version'])
    print(json.dumps(dict(fields=fields,payload=base64.b64encode(entity.SerializeToString()).decode())))
'''
        ts='''const log=console.log;console.log=()=>{};
const {processEntity}=require('./runtimes/typescript/dist/runtimes/typescript/main.js');
for(const row of JSON.parse(require('fs').readFileSync(0,'utf8'))) {
  const {entity,fields}=processEntity(Buffer.from(row.payload,'base64'),row.version);
  const {Entity}=require('./runtimes/typescript/dist/generated/ts/'+row.version+'/entity.js');
  log(JSON.stringify({fields,payload:Buffer.from(Entity.encode(entity).finish()).toString('base64')}));
}'''
        commands=[[sys.executable,'-c',py],['node','-e',ts],
                  ['dotnet',str(self.reflector/'bin/Release/net8.0/Decoder.dll'),str(workspace/'runtimes/csharp/bin/Release/net8.0/CsharpApp.dll')]]
        from testbed.pubsub.broker import Broker
        from testbed.pubsub.run import validate
        broker=Broker(nullable_fields=('name',))
        for runtime in fresh_oracle.RUNTIMES:
            broker.dispatch('/subscribe',dict(subscriber=runtime,runtime=runtime,topics=['entity.v1','entity.v2']))
        published=[]
        import hashlib
        for sample in samples:
            receipt=broker.dispatch('/publish',dict(topic=sample['topic'],payload=fresh_oracle.b64(sample['payload'])))
            published.append(dict(message_id=receipt['message_id'],topic=sample['topic'],fields=sample['fields'],
                sha256=hashlib.sha256(sample['payload']).hexdigest(),bytes=len(sample['payload'])))
        actual=[]
        for runtime,command in zip(fresh_oracle.RUNTIMES,commands):
            result=subprocess.run(command,cwd=workspace,env=self.env,input=data,capture_output=True,text=True,timeout=30)
            if result.returncode:raise ValueError(runtime+' decoder failed: '+result.stdout+result.stderr)
            # Requiring TS main prints its unchanged standalone sample first.
            rows=[json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')][-len(samples):]
            wanted=[]
            for sample in samples:
                fields=sample['fields']
                wire=fresh_oracle.text(1,fields['entity_id'])
                if fields.get('name') is not None:
                    wire+=fresh_oracle.text(2,fields['name'],present=True)
                wanted.append(dict(fields=fields,payload=fresh_oracle.b64(wire)))
            fresh_oracle.check_results(rows,wanted)
            for expected,row in zip(published,rows,strict=True):
                broker.dispatch('/ack',dict(subscriber=runtime,message_id=expected['message_id'],fields=row['fields']))
            actual.append(runtime)
        self.assertEqual(actual,list(fresh_oracle.RUNTIMES))
        validate(broker.state(),published)

    def exercise(self, name):
        case=adapted(self.source,name)
        directory=ROOT/'patchgen/reference'/name
        controls=json.loads((directory/'wrong-patches.json').read_text())
        with tempfile.TemporaryDirectory() as tmp:
            recipe=fresh_cases.propose(case,Path(tmp))
        self.assertEqual(recipe['diff'],(directory/'expected.patch').read_text())
        for row in [dict(patch='expected.patch'),*controls]:
            with self.subTest(case=name,patch=row['patch']):
                evidence=self.base/(name+'-'+row['patch']);evidence.mkdir()
                output=evidence/'proposal'
                proposal=dict(contract_version='1.0',outcome='patch',diff=(directory/row['patch']).read_text(),
                              rationale='Offline evaluator replay',confidence=0,assumptions=[])
                input_file=evidence/'input.json';input_file.write_text(json.dumps(case))
                command=[sys.executable,'-m','patchgen.generator','--source',self.source,'--fixture',input_file,
                    '--output',output,'--validation-profile',name]
                if row['patch']=='expected.patch':
                    command += ['--strategy','deterministic_fresh']
                else:
                    replay=evidence/'response.json';replay.write_text(json.dumps(proposal))
                    command += ['--strategy','candidate_edits','--response',replay]
                result=run(command,ROOT)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                generation=json.loads((output/'report.json').read_text())
                self.assertEqual(generation['status'],'applied_unvalidated')
                self.assertEqual(generation['mode'],'deterministic_proposal' if row['patch']=='expected.patch' else 'offline_replay')
                workspace=Path(generation['workspace'])
                try:
                    failure=self.build(workspace)
                    if not failure:
                        try:
                            if name == fresh_cases.PROFILES[0]:self.entity_decoders(workspace)
                            else:
                                result=run([sys.executable,output/'fresh-oracle-source.py','--root',workspace,
                                    '--case',name,'--output',output/'fresh'],output/'fresh-harness',self.env)
                                report=json.loads((output/'fresh/report.json').read_text())
                                if report['status'] != 'passed':raise ValueError(report.get('error'))
                                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                                fresh_oracle.check_evidence(output/'fresh',name,case['source_revision'])
                                if row['patch']=='expected.patch':
                                    # Exercise review integrity using the real retained CLI outputs.
                                    # This in-memory status tests the review checker, not the unrun transport gate.
                                    reviewed=dict(generation,status='validation_passed',fresh_validation=report)
                                    check_host_evidence(evidence,reviewed)
                                    record=output/'fresh/python.json';original=record.read_text()
                                    data=json.loads(original);values=json.loads(data['stdout'])
                                    values[0]['fields']['unexpected']=True;data['stdout']=json.dumps(values)
                                    record.write_text(json.dumps(data))
                                    with self.assertRaises(generator.ContractError):check_host_evidence(evidence,reviewed)
                                    record.write_text(original)
                        except ValueError as error:failure=str(error)
                    if row['patch']=='expected.patch':self.assertIsNone(failure,failure)
                    else:
                        self.assertTrue(failure,'wrong patch unexpectedly passed: '+row['reason'])
                        self.assertIn({'compile':'error CS','runtime':'csharp: runtime exited unsuccessfully',
                                       'oracle':'fresh wire/behavior mismatch',
                                       # Rejected earlier by an existing end-to-end test in the pipeline; the fresh oracle alone also rejects it.
                                       'tests':'fresh wire/behavior mismatch'}[row['rejected_by']],failure)
                finally:
                    run(['git','worktree','remove','--force',workspace],self.source)


def runtime_test(name):
    def test(self):self.exercise(name)
    return test


for _name in fresh_cases.PROFILES:
    setattr(FreshRuntimeTests,'test_'+_name.replace('-','_'),runtime_test(_name))


class FreshPipelineTests(unittest.TestCase):
    def test_fixed_gate_dispatches_every_fresh_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name in fresh_cases.PROFILES:
                case=fresh_cases.fixture(name)
                case['affected_files']=[]
                output=root/name;output.mkdir()
                commands=[]
                def command(args,cwd,log=None,timeout=300):
                    commands.append(args)
                    if args[:3]==['git','worktree','add']:
                        workspace=output/'workspace';workspace.mkdir()
                        schema=workspace/case['change']['schema_path'];schema.parent.mkdir(parents=True)
                        schema.write_text(case['change']['new_schema'])
                    elif str(output/'fresh-oracle-source.py') in args:
                        target=output/'fresh';target.mkdir()
                        (target/'report.json').write_text(json.dumps(dict(status='passed',case=name,
                            runtime_cases=fresh_oracle.count(name),runtime_revision=case['source_revision'])))
                    return ''
                with patch.object(generator,'verify_source'),patch.object(generator,'check_patch'),patch.object(generator,'command',side_effect=command):
                    generator.apply_and_validate(ROOT,case,dict(diff='patch'),output,True,({'fresh_case':name},''))
                self.assertIn(['buf','generate'],commands)
                self.assertIn([sys.executable,'run_local.py'],commands)
                invocation=next(c for c in commands if str(output/'fresh-oracle-source.py') in c)
                self.assertEqual(invocation[invocation.index('--case')+1],name)

    @unittest.skipIf(os.environ.get('SCHEMA_SENTINEL_SKIP_LOOPBACK') == '1',
                     'loopback/e2e disabled by SCHEMA_SENTINEL_SKIP_LOOPBACK')
    def test_full_pipeline_reference_controls_and_review_when_loopback_is_available(self):
        try:
            with socket.socket() as probe:probe.bind(('127.0.0.1',0))
        except OSError:
            self.skipTest('sandbox forbids loopback listeners; runtime decoder/CLI checks still run')
        for name in fresh_cases.PROFILES:
            directory=ROOT/'patchgen/reference'/name
            controls=json.loads((directory/'wrong-patches.json').read_text())
            for row in [dict(patch='expected.patch'),*controls]:
                with self.subTest(case=name,patch=row['patch']),tempfile.TemporaryDirectory() as tmp:
                    base=Path(tmp)
                    command=[sys.executable,'-m','patchgen.pipeline','--fixture',ROOT/'patchgen/fixtures'/name/'runtime-input.json',
                        '--output',base/'run','--local-codegen','--review-output',base/'review']
                    if row['patch']=='expected.patch':
                        command += ['--generate','--strategy','deterministic_fresh']
                    else:
                        replay=base/'response.json'
                        replay.write_text(json.dumps(dict(contract_version='1.0',outcome='patch',diff=(directory/row['patch']).read_text(),
                            rationale=row['reason'],confidence=0,assumptions=[])))
                        command += ['--response',replay]
                    result=run(command,ROOT)
                    report=json.loads((base/'run/proposal/report.json').read_text())
                    if row['patch']=='expected.patch':
                        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                        self.assertEqual(report['status'],'validation_passed')
                        check_host_evidence(base/'run',report)
                        self.assertTrue((base/'review/index.html').is_file())
                    else:
                        self.assertNotEqual(result.returncode,0)
                        self.assertEqual(report['status'],'failed')
                        if row['rejected_by']=='compile':
                            self.assertIn('error CS',(base/'run/proposal/validation.log').read_text())
                        elif row['rejected_by']=='tests':
                            self.assertIn('decoded different stable fields',report['error'])
                        else:
                            evidence=json.loads((base/'run/proposal/fresh/report.json').read_text())
                            self.assertEqual(evidence['status'],'failed')
                            self.assertIn('oracle rejected' if name==fresh_cases.PROFILES[0] else 'csharp: runtime exited unsuccessfully' if row['rejected_by']=='runtime' else 'fresh wire/behavior mismatch',evidence['error'])
