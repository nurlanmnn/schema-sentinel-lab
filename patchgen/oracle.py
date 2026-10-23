"""Independent field-removal oracle. Never included in model prompts."""
import importlib.util
import json
import os
import signal
from pathlib import Path
import subprocess
import sys
import time
import urllib.request


def main(workspace):
    root = Path(workspace).resolve()
    sys.path.insert(0, str(root / 'generated/python'))
    from v1.entity_pb2 import Entity
    from v2.entity_pb2 import Entity as EntityV2
    assert list(Entity.DESCRIPTOR.fields_by_name) == ['entity_id']
    assert list(EntityV2.DESCRIPTOR.fields_by_name) == ['entity_id']
    spec = importlib.util.spec_from_file_location('trusted_runner',root / 'testbed/scripts/run-local.py')
    runner = importlib.util.module_from_spec(spec); spec.loader.exec_module(runner)
    process = subprocess.Popen([sys.executable,str(root / 'testbed/scripts/run-local.py'),'--serve'],cwd=root,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,
                               creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0)
    try:
        for port in (8002, 8001, 8000):
            for _ in range(150):
                if process.poll() is not None:
                    raise AssertionError('services failed: ' + process.stdout.read())
                try:
                    with urllib.request.urlopen(f'http://127.0.0.1:{port}/health',timeout=1):
                        break
                except OSError:
                    time.sleep(.2)
            else:
                raise AssertionError(f'service readiness timeout on {port}')
        cases = [('normal','roundtrip-001'),('empty',''),('unicode','entity-雪-🚀'),('escaped','quotes "\n\\')]
        for label, identifier in cases + [('legacy','legacy-001')]:
            raw = Entity(entity_id=identifier).SerializeToString()
            if label == 'legacy':
                raw += b'\x12\x07retired'
            req = urllib.request.Request('http://127.0.0.1:8000/relay',data=raw,headers={'Content-Type':'application/x-protobuf'})
            with urllib.request.urlopen(req,timeout=15) as response:
                assert response.headers.get_content_type() == 'application/x-protobuf'
                decoded = Entity.FromString(response.read())
                observations = json.loads(response.headers['X-Schema-Sentinel-Observations'])
                trace = json.loads(response.headers['X-Service-Trace'])
            assert decoded.entity_id == identifier
            assert [o['runtime'] for o in observations] == ['python','typescript','csharp']
            assert all(o['fields'] == {'entity_id':identifier} for o in observations), observations
            assert trace == ['python','typescript','csharp']
            print(f'PASS independent oracle: {label}',flush=True)
    finally:
        # Interrupt lets the runner execute its finally block and stop all services.
        if process.poll() is None:
            process.send_signal(signal.CTRL_BREAK_EVENT if os.name == 'nt' else signal.SIGINT)
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                runner.stop_processes([process])
        print(process.stdout.read())


if __name__ == '__main__':
    main(sys.argv[1])
