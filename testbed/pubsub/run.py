"""Exercise actual three-runtime fan-out; use a new evidence output directory."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import urllib.request

from testbed.pubsub.broker import create_server

ROOT = Path(__file__).resolve().parents[2]
RUNTIMES = ['python', 'typescript', 'csharp']
TEXT_CASES = [('', ''), ('pubsub-001', 'Sensor A'), ('entity-雪-🚀', 'Café / Δ / 🚀'),
              ('quotes "\n\\', 'line\nbreak " \\')]


def wire_string(number, text):
    """Independent wire encoder, deliberately not generated protobuf code."""
    raw = text.encode('utf-8')
    if not raw:
        return b''
    size = len(raw)
    length = bytearray()
    while size > 127:
        length.append((size & 127) | 128)
        size >>= 7
    length.append(size)
    return bytes([number * 8 + 2]) + bytes(length) + raw


CASES = ('baseline', 'rename', 'removal', 'utf8')


def samples(case='baseline'):
    if case not in CASES:
        raise ValueError('Unknown pubsub validation case')
    name_field = 'display_name' if case == 'rename' else 'name'
    return [{'topic': 'entity.' + version, 'payload': wire_string(1, entity_id) + (wire_string(2, name) if version == 'v1' else b''),
             'fields': {'entity_id': entity_id, **({name_field: name} if version == 'v1' and case != 'removal' else {})}}
            for version in ('v1', 'v2') for entity_id, name in TEXT_CASES]


def request(url, path, data=None):
    req = urllib.request.Request(url + path, data=None if data is None else json.dumps(data).encode(),
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=5) as response:
        return json.load(response)


def validate(state, published):
    if set(state['subscribers']) != set(RUNTIMES):
        raise RuntimeError('Subscriber inventory differs from expected three runtimes')
    for runtime in RUNTIMES:
        if state['subscribers'][runtime] != {'runtime': runtime, 'topics': ['entity.v1', 'entity.v2'], 'pending': []}:
            raise RuntimeError(f'{runtime}: subscriptions/pending queue differ')
        actual = [ack for ack in state['acknowledgements'] if ack['subscriber'] == runtime]
        if len(actual) != len(published):
            raise RuntimeError(f'{runtime}: missing or duplicate acknowledgement')
        for ack, expected in zip(actual, published, strict=True):
            if (ack['runtime'], ack['message_id'], ack['topic'], ack['fields']) != (runtime, expected['message_id'], expected['topic'], expected['fields']):
                raise RuntimeError(f'{runtime}: decoded fields, topic or delivery order differ for {expected["message_id"]}')
    if len(state['publications']) != len(published):
        raise RuntimeError('Unexpected publication count')
    for record, expected in zip(state['publications'], published, strict=True):
        if (record['message_id'], record['topic'], record['sha256'], record['bytes'], sorted(record['recipients'])) != (
                expected['message_id'], expected['topic'], expected['sha256'], expected['bytes'], sorted(RUNTIMES)):
            raise RuntimeError('Publication identity/fan-out mismatch')


def execute(root, output, case='baseline'):
    if case not in CASES:
        raise RuntimeError('Unknown pubsub validation case')
    root, output = root.resolve(), output.resolve()
    if output.exists() or root == output or root.is_relative_to(output):
        raise RuntimeError('Use a new output directory that does not contain the runtime checkout')
    output.mkdir(parents=True)
    started = time.monotonic()
    report = {'status': 'failed', 'mode': 'actual_local_pubsub', 'case': case, 'runtime_root': str(root),
              'timing_scope': 'local publish-to-ack including polling, HTTP and decode; not schema propagation or human review',
              'human_approval_required': True, 'generated_patch_approval': False}
    processes, logs = [], []
    server = create_server()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f'http://127.0.0.1:{server.server_port}'
    published = []
    try:
        report['runtime_revision'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
        report['runtime_git_status'] = subprocess.check_output(['git', 'status', '--short', '--untracked-files=no'], cwd=root, text=True).splitlines()
        report['tools'] = {'python': sys.version, **{name: subprocess.check_output([name, '--version'], cwd=root, text=True).strip()
                                                   for name in ('node', 'dotnet')}}
        source_files = ['runtimes/python/main.py', 'runtimes/typescript/main.ts', 'runtimes/csharp/main.cs',
                        'proto/v1/entity.proto', 'proto/v2/entity.proto']
        report['runtime_source_sha256'] = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in source_files}
        report['harness_source_sha256'] = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                                          for path in [Path(__file__), Path(__file__).with_name('broker.py'), Path(__file__).with_name('topics.json')]}
        commands = [
            [sys.executable, str(root / 'runtimes/python/main.py'), '--subscribe'],
            ['node', str(root / 'runtimes/typescript/dist/runtimes/typescript/main.js'), '--subscribe'],
            ['dotnet', str(root / 'runtimes/csharp/bin/Release/net8.0/CsharpApp.dll'), '--subscribe'],
        ]
        for runtime, command in zip(RUNTIMES, commands, strict=True):
            log = (output / (runtime + '.log')).open('w')
            logs.append(log)
            processes.append(subprocess.Popen(command, cwd=root, env=dict(os.environ, PUBSUB_URL=url),
                                               stdout=log, stderr=subprocess.STDOUT))

        def wait_for(predicate, description):
            deadline = time.monotonic() + 25
            while True:
                for runtime, process in zip(RUNTIMES, processes, strict=True):
                    if process.poll() is not None:
                        raise RuntimeError(f'{runtime} subscriber exited; see its log')
                state = request(url, '/state')
                if predicate(state):
                    return state
                if time.monotonic() > deadline:
                    raise RuntimeError('Timed out waiting for ' + description)
                time.sleep(0.05)

        wait_for(lambda state: len(state['subscribers']) == 3, 'three subscriptions')
        # Publish the entire sequence without waiting for any consumer ack.
        for sample in samples(case):
            publication = request(url, '/publish', {'topic': sample['topic'], 'payload': base64.b64encode(sample['payload']).decode()})
            published.append({'message_id': publication['message_id'], 'topic': sample['topic'], 'fields': sample['fields'],
                              'sha256': hashlib.sha256(sample['payload']).hexdigest(), 'bytes': len(sample['payload'])})
        (output / 'expected.json').write_text(json.dumps(published, indent=2, ensure_ascii=True) + '\n')
        state = wait_for(lambda state: len(state['acknowledgements']) == len(published) * 3, 'all independent decoder acknowledgements')
        validate(state, published)
        report.update(status='passed', publication_cases=len(published), decoded_deliveries=len(state['acknowledgements']),
                      topics=2, runtimes=3)
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
        report['error'] = str(error)
    finally:
        (output / 'broker-state.json').write_text(json.dumps(server.broker.state(), indent=2) + '\n')
        for process in processes:
            if process.poll() is None:
                process.terminate()
        for process in processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        for log in logs:
            log.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        report['elapsed_seconds'] = time.monotonic() - started
        report['children_stopped'] = all(process.poll() is not None for process in processes)
        report['broker_stopped'] = not thread.is_alive()
        (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return int(report['status'] != 'passed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=CASES, default='baseline', help='independent semantic expectations; never inferred from runtime observations')
    parser.add_argument('--root', type=Path, default=ROOT, help='built runtime checkout (default: this checkout)')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        return execute(args.root, args.output, args.case)
    except (OSError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
