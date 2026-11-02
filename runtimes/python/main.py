"""Entity example and HTTP relay using the canonical generated bindings."""
import argparse
import base64
import time
import importlib
import json
import os
from pathlib import Path
import sys
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from socketserver import TCPServer
from google.protobuf.message import DecodeError

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "generated/python"))
OBSERVATIONS = "X-Schema-Sentinel-Observations"
TRACE = "X-Service-Trace"


class RelayServer(ThreadingHTTPServer):
    def server_bind(self):
        # HTTPServer normally does a reverse DNS lookup, which can delay startup.
        TCPServer.server_bind(self)
        self.server_name, self.server_port = self.server_address


def process_entity(raw_bytes: bytes, version: str):
    if version not in ("v1", "v2"):
        raise ValueError(f"Unsupported schema version: {version}")
    entity = importlib.import_module(f"{version}.entity_pb2").Entity.FromString(raw_bytes)
    fields = {"entity_id": entity.entity_id}
    if version == "v1":
        fields["name"] = entity.name
    print(json.dumps({"runtime": "python", "version": version, "fields": fields}, ensure_ascii=True), flush=True)
    return entity, fields


class Relay(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/health":
            self.send_error(404)
            return
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'{"status":"ok","runtime":"python"}')

    def do_POST(self):
        if self.path != "/relay":
            self.send_error(404)
            return
        try:
            entity, fields = process_entity(self.rfile.read(int(self.headers.get("Content-Length", "0"))), "v1")
            observation = {"runtime": "python", "fields": fields}
            request = urllib.request.Request(
                os.environ.get("TYPESCRIPT_RELAY_URL", "http://localhost:8001/relay"),
                data=entity.SerializeToString(), method="POST",
                headers={"Content-Type": "application/x-protobuf", TRACE: json.dumps(["python"])},
            )
            with urllib.request.urlopen(request, timeout=5) as downstream:
                body = downstream.read()
                observations = [observation] + json.loads(downstream.headers[OBSERVATIONS])
                trace = downstream.headers[TRACE]
            self.send_response(200)
            self.send_header("Content-Type", "application/x-protobuf")
            self.send_header("Content-Length", str(len(body)))
            self.send_header(OBSERVATIONS, json.dumps(observations, ensure_ascii=True))
            self.send_header(TRACE, trace)
            self.end_headers()
            self.wfile.write(body)
        except (ValueError, DecodeError) as error:
            self.send_error(400, str(error))
        except (OSError, KeyError) as error:
            self.send_error(502, str(error))


def subscribe():
    """Decode queued topic messages; an ack contains this runtime's fields."""
    broker = os.environ['PUBSUB_URL']
    if not broker.startswith('http://127.0.0.1:') or not broker.rsplit(':', 1)[-1].isdigit():
        raise ValueError('PUBSUB_URL must be a loopback HTTP port')
    subscriber = 'python'

    def post(path, data):
        request = urllib.request.Request(broker + path, data=json.dumps(data).encode(),
                                         headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.load(response)

    post('/subscribe', {'subscriber': subscriber, 'runtime': 'python', 'topics': ['entity.v1', 'entity.v2']})
    while True:
        delivery = post('/poll', {'subscriber': subscriber})['delivery']
        if delivery is None:
            time.sleep(0.05)
            continue
        if delivery['topic'] != 'entity.' + delivery['version']:
            raise ValueError('Topic/version mismatch')
        _, fields = process_entity(base64.b64decode(delivery['payload'], validate=True), delivery['version'])
        post('/ack', {'subscriber': subscriber, 'message_id': delivery['message_id'], 'fields': fields})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--subscribe", action="store_true")
    parser.add_argument("--telemetry", action="store_true")
    parser.add_argument("--inventory", action="store_true")
    parser.add_argument("--version", choices=["v1", "v2"], default="v1")
    args = parser.parse_args()
    if args.inventory:
        from inventory_runtime import run
        run()
    elif args.telemetry:
        from telemetry_runtime import run
        run()
    elif args.subscribe:
        subscribe()
    elif args.serve:
        with RelayServer((os.environ.get("HOST", "0.0.0.0"), int(os.environ.get("PORT", "8000"))), Relay) as server:
            print(f"Python listening on {server.server_address[0]}:{server.server_port}", flush=True)
            server.serve_forever()
    else:
        module = importlib.import_module(f"{args.version}.entity_pb2")
        entity = module.Entity(entity_id="py_101")
        if args.version == "v1":
            entity.name = "Sensor A"
        process_entity(entity.SerializeToString(), args.version)
