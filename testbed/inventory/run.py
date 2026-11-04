"""Independent signed-integer wire oracle; imports no generated bindings."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
CASES = ('baseline', 'width', 'zigzag')
ARTIFACTS = ('report.json', 'expected.json', 'python.json', 'typescript.json', 'csharp.json')


def varint(value):
    if not 0 <= value < 1 << 64:
        raise ValueError('varint outside uint64')
    result = bytearray()
    while value > 127:
        result.append((value & 127) | 128)
        value >>= 7
    result.append(value)
    return bytes(result)


def encode(sku, quantity, *, zigzag=False):
    bits = 32 if zigzag else 64
    if type(quantity) is not int or not -(1 << (bits - 1)) <= quantity < 1 << (bits - 1):
        raise ValueError(f'quantity outside int{bits}')
    raw = sku.encode('utf8')
    result = b'\x0a' + varint(len(raw)) + raw if raw else b''
    if quantity:
        encoded = ((quantity << 1) ^ (quantity >> 31)) if zigzag else quantity & ((1 << 64) - 1)
        result += b'\x10' + varint(encoded)
    return base64.b64encode(result).decode()


def requests(case='baseline'):
    if case not in CASES:
        raise ValueError('unknown inventory oracle case')
    values = [('empty-stock', 0), ('single', 1), ('backorder', -1),
              ('int32-max', (1 << 31) - 1), ('int32-min', -(1 << 31)),
              ('箱-α', 42), ('', 7), ('long-' + 'x' * 128, 123)]
    if case == 'width':
        values += [('above32', 1 << 31), ('below32', -(1 << 31) - 1),
                   ('safe-max', (1 << 53) - 1), ('safe-edge', 1 << 53),
                   ('unsafe-next', (1 << 53) + 1), ('unsafe-negative', -(1 << 53) - 1),
                   ('int64-max', (1 << 63) - 1), ('int64-min', -(1 << 63))]
    if case == 'zigzag':
        values += [('one-byte-min', -64), ('one-byte-max', 63), ('two-byte-negative', -65),
                   ('two-byte-positive', 64), ('two-byte-min', -8192), ('two-byte-max', 8191),
                   ('three-byte-negative', -8193), ('three-byte-positive', 8192)]
    return [dict(sku=sku, quantity=str(q), payload=encode(sku, q, zigzag=case == 'zigzag')) for sku, q in values]


def expected(case):
    return [dict(fields=dict(sku=r['sku'], quantity=r['quantity']),
                 in_stock=int(r['quantity']) > 0, constructed_payload=r['payload']) for r in requests(case)]


def check_results(actual, wanted):
    if not isinstance(actual, list) or len(actual) != len(wanted):
        raise ValueError('inventory result count mismatch')
    for index, (got, want) in enumerate(zip(actual, wanted, strict=True)):
        if (not isinstance(got, dict) or got != want or type(got.get('in_stock')) is not bool
                or not isinstance(got.get('fields'), dict)
                or type(got['fields'].get('quantity')) is not str):
            raise ValueError(f'inventory integer/wire/predicate mismatch at case {index}')


def run(root, output, case):
    root, output = root.resolve(), output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    report = dict(status='failed', case=case, runtime_revision=subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
        source_dirty=bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=root, text=True).strip()),
        source_sha256={str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                       for pattern in ('runtimes/**/*.*', 'proto/**/*.proto', 'generated/**/*.*', 'buf.gen.yaml')
                       for p in root.glob(pattern) if p.is_file() and not any(
                           part in ('node_modules', 'dist', 'bin', 'obj', '__pycache__') for part in p.relative_to(root).parts)},
        runtime_cases=0, model_requests=0,
        scope='authored valid canonical decimal inputs and signed integer wire cases; not arbitrary input or mixed-version safety')
    wanted = expected(case)
    (output / 'expected.json').write_text(json.dumps(dict(requests=requests(case), results=wanted), indent=2) + '\n')
    python = root / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    commands = {
        'python': [str(python), 'runtimes/python/main.py', '--inventory'],
        'typescript': ['node', 'runtimes/typescript/dist/runtimes/typescript/main.js', '--inventory'],
        'csharp': ['dotnet', 'runtimes/csharp/bin/Release/net8.0/CsharpApp.dll', '--inventory'],
    }
    try:
        for name, command in commands.items():
            process = subprocess.run(command, cwd=root, input=json.dumps(requests(case)), capture_output=True, text=True, timeout=20)
            record = dict(command=command, exit_code=process.returncode, stdout=process.stdout, stderr=process.stderr)
            (output / (name + '.json')).write_text(json.dumps(record, indent=2) + '\n')
            if process.returncode:
                raise ValueError(f'{name} inventory process exited {process.returncode}')
            check_results(json.loads(process.stdout), wanted)
            report['runtime_cases'] += len(wanted)
        report['status'] = 'passed'
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        report['error'] = str(error)
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--case', choices=CASES, default='baseline')
    args = parser.parse_args()
    report = run(args.root, args.output, args.case)
    print(json.dumps(report, indent=2))
    return int(report['status'] != 'passed')


if __name__ == '__main__':
    raise SystemExit(main())
