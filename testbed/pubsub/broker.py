"""Bounded loopback-only in-memory fan-out; see decision 0012."""
import base64
import copy
import hashlib
import json
from pathlib import Path
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TOPICS = json.loads((Path(__file__).with_name('topics.json')).read_text())
RUNTIMES = ('python', 'typescript', 'csharp')


class Broker:
    def __init__(self):
        self.subscribers = {}
        self.publications = []
        self.acknowledgements = []
        self.lock = threading.Lock()

    def dispatch(self, path, data):
        if not isinstance(data, dict):
            raise ValueError('Body must be an object')
        with self.lock:
            if path == '/subscribe':
                subscriber, runtime, topics = (data.get(key) for key in ('subscriber', 'runtime', 'topics'))
                if not isinstance(subscriber, str) or not re.fullmatch(r'[a-z0-9-]{1,40}', subscriber):
                    raise ValueError('Invalid subscriber ID')
                if subscriber in self.subscribers or len(self.subscribers) >= 32:
                    raise ValueError('Duplicate ID or subscriber capacity reached')
                if runtime not in RUNTIMES or not isinstance(topics, list) or not topics:
                    raise ValueError('Invalid runtime/topics')
                if any(not isinstance(topic, str) or topic not in TOPICS for topic in topics) or len(set(topics)) != len(topics):
                    raise ValueError('Unknown or duplicate topic')
                self.subscribers[subscriber] = {'runtime': runtime, 'topics': topics[:], 'queue': []}
                return {'subscribed': subscriber}
            if path == '/publish':
                topic, payload = data.get('topic'), data.get('payload')
                if not isinstance(topic, str) or topic not in TOPICS or not isinstance(payload, str):
                    raise ValueError('Invalid topic/payload')
                try:
                    raw = base64.b64decode(payload, validate=True)
                except (ValueError, TypeError) as error:
                    raise ValueError('Payload must be strict base64') from error
                if len(raw) > 32768 or len(self.publications) >= 256:
                    raise ValueError('Payload/publication capacity reached')
                message_id = len(self.publications) + 1
                recipients = [name for name, item in self.subscribers.items() if topic in item['topics']]
                delivery = {'message_id': message_id, 'topic': topic, 'version': TOPICS[topic]['version'], 'payload': payload}
                for name in recipients:
                    self.subscribers[name]['queue'].append(copy.deepcopy(delivery))
                self.publications.append({'message_id': message_id, 'topic': topic, 'recipients': recipients,
                                          'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw),
                                          'published_monotonic': time.monotonic()})
                return {'message_id': message_id, 'recipients': recipients}
            if path not in ('/poll', '/ack'):
                raise KeyError('Unknown route')
            subscriber = data.get('subscriber')
            if not isinstance(subscriber, str) or subscriber not in self.subscribers:
                raise ValueError('Unknown subscriber')
            queue = self.subscribers[subscriber]['queue']
            if path == '/poll':
                return {'delivery': copy.deepcopy(queue[0]) if queue else None}
            message_id, fields = data.get('message_id'), data.get('fields')
            if type(message_id) is not int or not queue or queue[0]['message_id'] != message_id:
                raise ValueError('Acknowledgement must match the pending head')
            if not isinstance(fields, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in fields.items()):
                raise ValueError('Observation fields must be string-to-string')
            delivery = queue.pop(0)
            self.acknowledgements.append({'subscriber': subscriber, 'runtime': self.subscribers[subscriber]['runtime'],
                                         'message_id': message_id, 'topic': delivery['topic'], 'fields': fields.copy(),
                                         'publish_to_ack_seconds': time.monotonic() - self.publications[message_id - 1]['published_monotonic']})
            return {'acknowledged': message_id}

    def state(self):
        with self.lock:
            return copy.deepcopy({'topics': TOPICS, 'subscribers': {
                name: {'runtime': item['runtime'], 'topics': item['topics'],
                       'pending': [delivery['message_id'] for delivery in item['queue']]}
                for name, item in self.subscribers.items()},
                'publications': self.publications, 'acknowledgements': self.acknowledgements})


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.0'

    def log_message(self, *_):
        pass

    def respond(self, status, data):
        raw = json.dumps(data, ensure_ascii=True).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        self.respond(200, self.server.broker.state()) if self.path == '/state' else self.respond(404, {'error': 'Unknown route'})

    def do_POST(self):
        try:
            if self.headers.get_content_type() != 'application/json' or self.headers.get('Transfer-Encoding'):
                raise ValueError('Use Content-Length and application/json')
            size = int(self.headers.get('Content-Length', '-1'))
            if size < 0 or size > 65536:
                raise ValueError('Invalid body size')
            self.connection.settimeout(3)
            raw = self.rfile.read(size)
            if len(raw) != size:
                raise ValueError('Truncated body')
            self.respond(200, self.server.broker.dispatch(self.path, json.loads(raw)))
        except KeyError as error:
            self.respond(404, {'error': str(error)})
        except (ValueError, OSError) as error:
            self.respond(400, {'error': str(error)})


def create_server():
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    server.daemon_threads = True
    server.broker = Broker()
    return server
