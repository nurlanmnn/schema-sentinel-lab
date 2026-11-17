"""Independent synthetic wire vectors for fresh screening. No generated code or recipes.

This file is copied with the existing pub/sub harness before validation, outside
of the proposed patch. Expected outputs are determined before executing runtimes.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import struct
import socket
import time
import urllib.request
import subprocess
import sys

CASES = ('fresh-entity-name-presence', 'fresh-telemetry-speed-presence',
         'fresh-telemetry-asset-rename', 'fresh-inventory-quantity-unsigned', 'fresh-inventory-state-bool')
RUNTIMES = ('python', 'typescript', 'csharp')
ARTIFACTS = ('report.json', 'expected.json', 'python.json', 'typescript.json', 'csharp.json')
RELAY_ARTIFACTS = ('relay.json','relay-python.log','relay-typescript.log','relay-csharp.log')
PUBSUB_ARTIFACTS = ('report.json', 'expected.json', 'broker-state.json', 'python.log', 'typescript.log', 'csharp.log')


def varint(value):
    value &= (1 << 64) - 1
    out = bytearray()
    while value >= 128:
        out.append((value & 127) | 128)
        value >>= 7
    return bytes(out) + bytes([value])


def text(tag, value, present=False):
    raw = value.encode('utf8')
    return varint(tag * 8 + 2) + varint(len(raw)) + raw if raw or present else b''


def number(tag, value):
    return varint(tag * 8) + varint(value) if value else b''


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def b64(raw):
    return base64.b64encode(raw).decode()


def telemetry_wire(identifier, speed, optional=False):
    return text(1, identifier) + (b'\x15' + struct.pack('<f', speed)
        if speed is not None and (speed != 0 or optional) else b'')


def inventory_wire(sku, quantity, state, labels=(), warehouse='', drop_zone=''):
    return (text(1, sku) + number(2, quantity) + number(3, state)
            + b''.join(text(4, label, present=True) for label in labels)
            + text(7, warehouse) + text(8, drop_zone))


def entity_samples(case=None):
    values = [('', None), ('explicit-empty', ''), ('absent', None), ('雪-🚀', 'Café / Δ / 🚀'),
              ('whitespace', '  Sensor A  '), ('escaped', 'line\nbreak " \\'),
              ('long-' + 'a' * 130, 'b' * 140)]
    result = []
    for identifier, name in values:
        result.append(dict(topic='entity.v1', payload=text(1, identifier) + (text(2, name, present=True) if name is not None else b''),
                           fields=dict(entity_id=identifier, name=name)))
    # Last occurrence wins for optional scalars; distinguish last explicit empty.
    result.append(dict(topic='entity.v1', payload=text(1, 'last') + text(2, 'old') + text(2, '', present=True),
                       fields=dict(entity_id='last', name='')))
    for identifier in ('', 'v2-雪', '  v2  ', 'quote"\\\n'):
        result.append(dict(topic='entity.v2', payload=text(1, identifier), fields=dict(entity_id=identifier)))
    return result


def vectors(case):
    """Producer and consumer values deliberately differ, so echoing cannot pass."""
    if case == CASES[0]:
        return [], []
    requests, results = [], []
    if case in CASES[1:3]:
        # Explicit float32 extrema and immediate representable threshold neighbors.
        pairs = [(None, 31.0), (0.0, None), (-1.0, 0.0), (30.0, -1.0),
                 (31.0, 30.0), (None, 30.000001907348633), (12.5, 29.999998092651367),
                 (3.4028234663852886e38, -3.4028234663852886e38),
                 (-3.4028234663852886e38, 3.4028234663852886e38), (0.125, 12.5), (1.5, 31.0)]
        for index, (produce, consume) in enumerate(pairs):
            identifier = ('', '雪-🚀', '  asset  ', 'quote"\\\n')[index % 4]
            incoming = '' if index == 0 else 'wire-' + identifier
            optional = case == CASES[1]
            if not optional:
                produce = 0.0 if produce is None else produce
                consume = 0.0 if consume is None else consume
            request = dict(vehicle_id=identifier, payload=b64(telemetry_wire(incoming, consume, optional)))
            if index != 0 or not optional:
                request['speed'] = produce
            else:
                # First missing producer differs from explicit null in the sixth vector.
                produce = None
            requests.append(request)
            results.append(dict(fields={('vehicle_id' if optional else 'asset_id'): incoming,
                'speed_mps': None if consume is None else f32(consume)},
                speeding=consume is not None and f32(consume) > 30,
                constructed_payload=b64(telemetry_wire(identifier, produce, optional))))
    elif case == CASES[3]:
        values = [('0', 4294967295, 0), ('-1', 1, 0), ('4294967295', 0, 0),
                  ('4294967296', 2147483648, 0), ('2147483648', 2147483647, 0),
                  ('-4294967296', 1, 1), ('9223372036854775807', 1, 99),
                  ('-9223372036854775808', 1, -1), ('17', 17, 0), ('1', 1, 0)]
        for index, (produce, consume, state) in enumerate(values):
            sku = ('', 'SKU-雪', '  SKU  ', 'quote"\\\n')[index % 4]
            labels = ['', 'label-雪'] if index % 2 else []
            warehouse, drop = ('A', 'B') if index % 2 else ('', '')
            request = dict(sku=sku, quantity=produce, include_state=True, include_route=True,
                display_labels=labels, warehouse=warehouse, drop_zone=drop,
                payload=b64(inventory_wire('wire-' + sku, consume, state, labels, warehouse, drop)))
            requests.append(request)
            results.append(dict(fields=dict(sku='wire-' + sku, quantity=str(consume), display_labels=labels,
                warehouse=warehouse, drop_zone=drop, state_label={0:'UNSPECIFIED',1:'QUARANTINED'}.get(state,'UNKNOWN')),
                in_stock=consume > 0 and state == 0,
                constructed_payload=b64(inventory_wire(sku, min(4294967295, max(0, int(produce))), 0, labels, warehouse, drop))))
    elif case == CASES[4]:
        values = [(None, 1, 0), (True, 1, 1), (False, 0, 0), (False, -1, 0),
                  (True, 2147483647, 2), (False, -2147483648, 99),
                  (None, 1, -1), (False, 1, 2147483647), (True, 1, 0), (None, 0, 1)]
        for index, (quarantined, quantity, state) in enumerate(values):
            sku = ('', 'SKU-雪', '  SKU  ', 'quote"\\\n')[index % 4]
            labels = ['one', '', '二'] if index % 2 else []
            produce = (-2147483648, 0, 2147483647, -1, 1)[index % 5]
            request = dict(sku=sku, quantity=str(produce), include_state=True, include_route=True, display_labels=labels,
                warehouse='A', drop_zone='B', payload=b64(inventory_wire('wire-' + sku, quantity, state, labels, 'A', 'B')))
            if quarantined is not None:
                request['quarantined'] = quarantined
            requests.append(request)
            results.append(dict(fields=dict(sku='wire-' + sku, quantity=str(quantity), display_labels=labels,
                warehouse='A', drop_zone='B', state_label='QUARANTINED' if state else 'UNSPECIFIED'),
                in_stock=quantity > 0 and not state,
                constructed_payload=b64(inventory_wire(sku, produce, bool(quarantined), labels, 'A', 'B'))))
    else:
        raise ValueError('unknown fresh oracle')
    return requests, results


def count(case):
    return (len(entity_samples()) + len(relay_expected()) if case == CASES[0] else len(vectors(case)[0])) * 3


def check_results(actual, wanted):
    if not isinstance(actual, list) or len(actual) != len(wanted):
        raise ValueError('fresh runtime result count mismatch')
    for index, (got, want) in enumerate(zip(actual, wanted, strict=True)):
        # JSON booleans compare equal to 0/1 in Python; enforce the entire JSON type tree.
        def same(left, right, key=None):
            if isinstance(right, dict):
                return isinstance(left, dict) and left.keys() == right.keys() and all(same(left[k], v, k) for k,v in right.items())
            if isinstance(right, list):
                return isinstance(left, list) and len(left) == len(right) and all(same(a,b) for a,b in zip(left,right))
            if type(right) in (int,float):
                if type(left) not in (int, float):
                    return False
                if key == 'speed_mps':
                    try:
                        return struct.unpack('f', struct.pack('f', left))[0] == right
                    except (OverflowError, struct.error):
                        return False
                return left == right
            return type(left) is type(right) and left == right
        if not same(got, want):
            differences = [key for key in want if not same(got.get(key), want[key])] if isinstance(got,dict) else ['row']
            raise ValueError(f'fresh wire/behavior mismatch at vector {index}: {", ".join(differences)}')


def relay_expected():
    result = []
    for sample in entity_samples():
        if sample['topic'] != 'entity.v1':
            continue
        fields = sample['fields']
        wire = text(1, fields['entity_id'])
        if fields['name'] is not None:
            wire += text(2, fields['name'], present=True)
        result.append(dict(payload=b64(wire), observations=[dict(runtime=r,fields=fields) for r in RUNTIMES],trace=list(RUNTIMES)))
    return result


def run_entity_relay(root, output):
    """Check presence on the returned wire, beyond the independently decoded observations."""
    commands = {
        'csharp':['dotnet',str(root/'runtimes/csharp/bin/Release/net8.0/CsharpApp.dll'),'--serve'],
        'typescript':['node',str(root/'runtimes/typescript/dist/runtimes/typescript/main.js'),'--serve'],
        'python':[sys.executable,str(root/'runtimes/python/main.py'),'--serve'],
    }
    processes, logs = [], []
    record = dict(status='failed',results=[],children_stopped=False)
    try:
        for port in (8000,8001,8002):
            with socket.socket() as probe:
                probe.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
                probe.bind(('127.0.0.1',port))
        for runtime, command in commands.items():
            log=(output/('relay-'+runtime+'.log')).open('w');logs.append(log)
            env=dict(os.environ,ASPNETCORE_URLS='http://127.0.0.1:8002',HOST='127.0.0.1',
                     PORT='8001' if runtime=='typescript' else '8000',
                     TYPESCRIPT_RELAY_URL='http://127.0.0.1:8001/relay',CSHARP_RELAY_URL='http://127.0.0.1:8002/relay')
            processes.append(subprocess.Popen(command,cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT))
        deadline=time.monotonic()+30
        for port in (8002,8001,8000):
            while True:
                if any(p.poll() is not None for p in processes):
                    raise ValueError('fresh relay stopped during startup')
                try:
                    with urllib.request.urlopen(f'http://127.0.0.1:{port}/health',timeout=1) as response:
                        if response.status == 200:break
                except OSError:
                    pass
                if time.monotonic() >= deadline:raise ValueError('fresh relay readiness timeout')
                time.sleep(0.1)
        for sample in entity_samples():
            if sample['topic'] != 'entity.v1':continue
            request=urllib.request.Request('http://127.0.0.1:8000/relay',data=sample['payload'],
                headers={'Content-Type':'application/x-protobuf'})
            with urllib.request.urlopen(request,timeout=15) as response:
                if response.headers.get_content_type() != 'application/x-protobuf':
                    raise ValueError('fresh relay response type mismatch')
                record['results'].append(dict(payload=b64(response.read()),
                    observations=json.loads(response.headers['X-Schema-Sentinel-Observations']),
                    trace=json.loads(response.headers['X-Service-Trace'])))
        check_results(record['results'],relay_expected())
        record['status']='passed'
    except (OSError,ValueError,subprocess.SubprocessError) as error:
        record['error']=str(error)
    finally:
        for process in processes:
            if process.poll() is None:process.terminate()
        for process in processes:
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill();process.wait()
        for log in logs:log.close()
        record['children_stopped']=all(p.poll() is not None for p in processes)
        (output/'relay.json').write_text(json.dumps(record,indent=2)+'\n')
    return record


def run(root, output, case):
    root, output = root.resolve(), output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    report = dict(status='failed', case=case, runtime_cases=0, model_requests=0,
                  runtime_revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip())
    try:
        if case == CASES[0]:
            # Absolute-script execution does not put cwd on sys.path.
            harness = Path(__file__).with_name('fresh-harness')
            if harness.is_dir():
                sys.path.insert(0, str(harness))
            from testbed.pubsub import run as pubsub
            if pubsub.execute(root, output/'pubsub', case, sample_provider=entity_samples, nullable_fields=('name',)):
                raise ValueError('fresh presence pub/sub oracle rejected decoded fields')
            # Same malformed-wire check used by the development live pub/sub route.
            if pubsub.execute(root, output/'malformed', case, 'malformed', sample_provider=entity_samples, nullable_fields=('name',)):
                raise ValueError('fresh pub/sub malformed probe failed')
            relay = run_entity_relay(root,output)
            if relay['status'] != 'passed' or not relay['children_stopped']:
                raise ValueError('fresh relay presence oracle rejected returned wire')
            report['runtime_cases'] = count(case)
        else:
            data, wanted = vectors(case)
            (output/'expected.json').write_text(json.dumps(dict(requests=data, results=wanted),indent=2)+'\n')
            python = root/'.venv'/('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
            mode = '--telemetry' if case in CASES[1:3] else '--inventory'
            commands = ([str(python), 'runtimes/python/main.py', mode],
                        ['node', 'runtimes/typescript/dist/runtimes/typescript/main.js', mode],
                        ['dotnet', 'runtimes/csharp/bin/Release/net8.0/CsharpApp.dll', mode])
            failures = []
            for runtime, command in zip(RUNTIMES, commands, strict=True):
                process = subprocess.run(command, cwd=root, input=json.dumps(data),capture_output=True,text=True,timeout=30)
                record = dict(command=command, exit_code=process.returncode, stdout=process.stdout, stderr=process.stderr)
                (output/(runtime+'.json')).write_text(json.dumps(record,indent=2)+'\n')
                try:
                    if process.returncode:
                        raise ValueError('runtime exited unsuccessfully')
                    check_results(json.loads(process.stdout), wanted)
                    report['runtime_cases'] += len(wanted)
                except ValueError as error:
                    failures.append(runtime + ': ' + str(error))
            if failures:
                raise ValueError('; '.join(failures))
        report['status'] = 'passed'
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        report['error'] = str(error)
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--case', choices=CASES, required=True)
    args = parser.parse_args()
    report = run(args.root,args.output,args.case)
    print(json.dumps(report,indent=2))
    return int(report['status'] != 'passed')


def check_evidence(root, case, revision):
    """Recheck retained runtime outputs when exporting or verifying human review."""
    report = json.loads((root/'report.json').read_text())
    if (report.get('status') != 'passed' or report.get('case') != case
            or report.get('runtime_cases') != count(case) or report.get('runtime_revision') != revision):
        raise ValueError('fresh evidence identity or count mismatch')
    if case == CASES[0]:
        from testbed.pubsub.run import validate, validate_malformed
        published = json.loads((root/'pubsub/expected.json').read_text())
        samples = entity_samples()
        if len(published) != len(samples):
            raise ValueError('fresh pubsub sample count mismatch')
        for item, sample in zip(published,samples,strict=True):
            if any(item[k] != v for k,v in dict(topic=sample['topic'],fields=sample['fields'],
                    sha256=hashlib.sha256(sample['payload']).hexdigest(),bytes=len(sample['payload'])).items()):
                raise ValueError('fresh pubsub expectations changed')
        validate(json.loads((root/'pubsub/broker-state.json').read_text()),published)
        passing = json.loads((root/'pubsub/report.json').read_text())
        malformed = json.loads((root/'malformed/report.json').read_text())
        for record, status in ((passing,'passed'),(malformed,'expected_rejection_observed')):
            if (record.get('case') != case or record.get('status') != status or record.get('runtime_revision') != revision
                    or not record.get('children_stopped') or not record.get('broker_stopped')):
                raise ValueError('fresh pubsub process evidence mismatch')
        if passing.get('decoded_deliveries') != len(entity_samples()) * 3:
            raise ValueError('fresh pubsub delivery count mismatch')
        relay = json.loads((root/'relay.json').read_text())
        if relay.get('status') != 'passed' or relay.get('children_stopped') is not True:
            raise ValueError('fresh relay process evidence mismatch')
        check_results(relay.get('results'),relay_expected())
        malformed_expected = json.loads((root/'malformed/expected.json').read_text())
        if malformed_expected.get('payload_hex') != '0a0561':
            raise ValueError('fresh malformed payload changed')
        validate_malformed(json.loads((root/'malformed/broker-state.json').read_text()),malformed_expected['message_id'],
                           malformed['subscriber_exit_codes'],malformed['decoder_failures'])
        signatures = {'python': ('google.protobuf.message.DecodeError:',),
                      'typescript': ('RangeError: index out of range:', 'Reader.read_string'),
                      'csharp': ('Google.Protobuf.InvalidProtocolBufferException:',)}
        for runtime,tokens in signatures.items():
            content = (root/'malformed'/(runtime+'.log')).read_text()
            if not all(token in content for token in tokens):
                raise ValueError('fresh malformed decoder log mismatch')
    else:
        data, wanted = vectors(case)
        if json.loads((root/'expected.json').read_text()) != dict(requests=data,results=wanted):
            raise ValueError('fresh oracle expected vectors changed')
        for runtime in RUNTIMES:
            record = json.loads((root/(runtime+'.json')).read_text())
            if type(record.get('exit_code')) is not int or record['exit_code'] != 0:
                raise ValueError('fresh runtime did not exit successfully')
            check_results(json.loads(record['stdout']),wanted)
    return report


if __name__ == '__main__':
    raise SystemExit(main())
