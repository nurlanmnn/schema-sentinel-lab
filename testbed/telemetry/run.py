"""Check real telemetry bindings against independently encoded wire/behavior cases.

No generated binding or reference patch is imported by this evaluator.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ('report.json', 'expected.json', 'python.json', 'typescript.json', 'csharp.json')


def requests(case="baseline"):
    # Baseline values are exactly representable float32; precision adds binary64 inputs.
    # Strict >30 boundary is intentional.
    values = [('stopped', 0.0), ('below', 29.5), ('boundary', 30.0), ('above', 30.5),
              ('reverse', -1.0), ('車-α', 12.5), ('', 4.0), ('fast', 256.0)]
    if case == 'precision':
        values += [('fraction-above',30.0000001),('fraction-below',29.9999999),('wide',16777217.25)]
    result = []
    for vehicle, speed in values:
        encoded = vehicle.encode('utf8')
        wire = (b'\x0a' + bytes([len(encoded)]) + encoded if encoded else b'')
        if speed:
            wire += (b'\x11' + struct.pack('<d', speed) if case == 'precision' else b'\x15' + struct.pack('<f', speed))
        result.append(dict(vehicle_id=vehicle, speed=speed, payload=base64.b64encode(wire).decode()))
    return result


def expected(case):
    if case not in ('baseline', 'rename', 'precision'):
        raise ValueError('unknown telemetry oracle case')
    key = 'ground_speed_mps' if case == 'rename' else 'speed_mps'
    return [dict(fields=dict(vehicle_id=r['vehicle_id'], **{key:r['speed']}),
                 speeding=r['speed'] > 30, constructed_payload=r['payload']) for r in requests(case)]


def check_results(actual, wanted):
    if not isinstance(actual, list) or len(actual) != len(wanted):
        raise ValueError('telemetry runtime result count mismatch')
    for index, (got, want) in enumerate(zip(actual, wanted, strict=True)):
        # bool equals 0/1 in Python; enforce types as well as values.
        if (not isinstance(got, dict) or got != want or type(got.get('speeding')) is not bool
                or not isinstance(got.get('fields'), dict)
                or any(type(v) is bool for v in got['fields'].values())):
            raise ValueError(f'telemetry wire/units/threshold mismatch at case {index}')


def run(root, output, case):
    root, output = root.resolve(), output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    report = dict(status='failed', case=case, runtime_revision=subprocess.check_output(
        ['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
        source_dirty=bool(subprocess.check_output(['git','status','--porcelain'],cwd=root,text=True).strip()),
        source_sha256={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
                       for pattern in ('runtimes/**/*.*', 'proto/**/*.proto', 'generated/**/*.*')
                       for p in root.glob(pattern) if p.is_file() and not any(
                           part in ('node_modules','dist','bin','obj','__pycache__') for part in p.relative_to(root).parts)},
        runtime_cases=0, model_requests=0, scope='authored '+('float64' if case=='precision' else 'float32')+' cases; not arbitrary wire, units or mixed-version safety')
    wanted = expected(case)
    (output/'expected.json').write_text(json.dumps(dict(requests=requests(case), results=wanted),indent=2)+'\n')
    python = root/'.venv'/('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    commands = {
        'python':[str(python), 'runtimes/python/main.py', '--telemetry'],
        'typescript':['node', 'runtimes/typescript/dist/runtimes/typescript/main.js', '--telemetry'],
        'csharp':['dotnet', 'runtimes/csharp/bin/Release/net8.0/CsharpApp.dll', '--telemetry'],
    }
    try:
        for name, command in commands.items():
            process = subprocess.run(command,cwd=root,input=json.dumps(requests(case)),capture_output=True,text=True,timeout=20)
            # Retain failed stdout/stderr too; a failed executable is never a migration success.
            record = dict(command=command, exit_code=process.returncode, stdout=process.stdout, stderr=process.stderr)
            (output/(name+'.json')).write_text(json.dumps(record,indent=2)+'\n')
            if process.returncode:
                raise ValueError(f'{name} telemetry process exited {process.returncode}')
            check_results(json.loads(process.stdout), wanted)
            report['runtime_cases'] += len(wanted)
        report['status'] = 'passed'
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        report['error'] = str(error)
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--case',choices=('baseline','rename','precision'),default='baseline')
    args = parser.parse_args()
    report = run(args.root,args.output,args.case)
    print(json.dumps(report,indent=2))
    return int(report['status'] != 'passed')


if __name__ == '__main__':
    raise SystemExit(main())
