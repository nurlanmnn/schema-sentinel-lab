import base64
import copy
import json
from pathlib import Path
import sys
import threading
import unittest
import urllib.error
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from testbed.pubsub.broker import Broker, create_server
from testbed.pubsub.run import samples, validate, wire_string


class BrokerTests(unittest.TestCase):
    def setUp(self):
        self.broker = Broker()

    def sub(self, name, topics):
        return self.broker.dispatch('/subscribe', {'subscriber': name, 'runtime': 'python', 'topics': topics})

    def publish(self, topic='entity.v1', raw=b''):
        return self.broker.dispatch('/publish', {'topic': topic, 'payload': base64.b64encode(raw).decode()})

    def poll(self, subscriber):
        return self.broker.dispatch('/poll', {'subscriber': subscriber})['delivery']

    def ack(self, subscriber, message_id):
        return self.broker.dispatch('/ack', {'subscriber': subscriber, 'message_id': message_id, 'fields': {'entity_id': 'actual'}})

    def test_fanout_isolation_independent_fifo_and_poll_redelivery(self):
        self.sub('a', ['entity.v1']); self.sub('b', ['entity.v1']); self.sub('c', ['entity.v2'])
        self.assertEqual(self.publish(raw=b'one')['recipients'], ['a', 'b'])
        self.publish(raw=b'two')
        first = self.poll('a')
        self.assertEqual(first, self.poll('a'))
        self.assertEqual(first['message_id'], 1)
        self.assertIsNone(self.poll('c'))
        first['payload'] = 'tampered'
        self.assertNotEqual(first, self.poll('a'))
        self.ack('a', 1)
        self.assertEqual(self.poll('a')['message_id'], 2)
        self.assertEqual(self.poll('b')['message_id'], 1)
        self.assertEqual(self.broker.state()['acknowledgements'][0]['fields'], {'entity_id': 'actual'})

    def test_no_history_replay(self):
        self.assertEqual(self.publish()['recipients'], [])
        self.sub('later', ['entity.v1'])
        self.assertIsNone(self.poll('later'))

    def test_invalid_ack_does_not_mutate_and_duplicate_rejects(self):
        self.sub('a', ['entity.v1']); self.publish(); self.publish()
        before = self.broker.state()
        for message_id in (2, True, None, -1):
            with self.assertRaises(ValueError):
                self.ack('a', message_id)
            self.assertEqual(before, self.broker.state())
        self.ack('a', 1)
        with self.assertRaises(ValueError):
            self.ack('a', 1)
        self.assertEqual(self.poll('a')['message_id'], 2)

    def test_bad_requests_and_capacity(self):
        for topic, payload in [('missing', ''), ('entity.v1', 'not base64!'), ('entity.v1', None), ({}, '')]:
            with self.assertRaises(ValueError):
                self.broker.dispatch('/publish', {'topic': topic, 'payload': payload})
        for topics in ([], ['missing'], ['entity.v1', 'entity.v1'], [{}]):
            with self.assertRaises(ValueError):
                self.sub('a', topics)
        self.sub('a', ['entity.v1'])
        with self.assertRaises(ValueError):
            self.sub('a', ['entity.v1'])
        with self.assertRaises(ValueError):
            self.publish(raw=b'x' * 32769)
        with self.assertRaises(ValueError):
            self.poll('unknown')
        for _ in range(256):
            self.publish()
        with self.assertRaises(ValueError):
            self.publish()

    def test_observation_shape_rejected_before_queue_mutation(self):
        self.sub('a', ['entity.v1']); self.publish()
        before = self.broker.state()
        for fields in (None, [], {'entity_id': 10}):
            with self.assertRaises(ValueError):
                self.broker.dispatch('/ack', {'subscriber': 'a', 'message_id': 1, 'fields': fields})
            self.assertEqual(before, self.broker.state())

    def test_independent_wire_encoder_known_bytes(self):
        self.assertEqual(wire_string(1, 'A') + wire_string(2, 'B'), bytes.fromhex('0a0141120142'))
        self.assertEqual(wire_string(1, ''), b'')
        self.assertEqual(wire_string(1, 'a' * 128)[:3], b'\x0a\x80\x01')
        self.assertEqual(len(samples()), 8)


class HttpBrokerTests(unittest.TestCase):
    def test_real_http_malformed_routes_types_and_success(self):
        server = create_server()
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        url = f'http://127.0.0.1:{server.server_port}'
        try:
            for route, raw, content_type, status in [('/publish', b'{', 'application/json', 400),
                    ('/publish', b'[]', 'application/json', 400), ('/publish', b'{}', 'text/plain', 400),
                    ('/publish', b'x' * 65537, 'application/json', 400), ('/unknown', b'{}', 'application/json', 404)]:
                req = urllib.request.Request(url + route, data=raw, headers={'Content-Type': content_type})
                with self.assertRaises(urllib.error.HTTPError) as error:
                    urllib.request.urlopen(req, timeout=3)
                self.assertEqual(error.exception.code, status)
                error.exception.close()
            req = urllib.request.Request(url + '/publish', data=b'{"topic":"entity.v1","payload":""}', headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=3) as response:
                self.assertEqual(json.load(response), {'message_id': 1, 'recipients': []})
        finally:
            server.shutdown(); server.server_close(); thread.join(timeout=5)


class EvidenceTests(unittest.TestCase):
    def test_corrupt_evidence_missing_duplicated_reordered_and_wrong_fields_reject(self):
        published = [{'message_id': i, 'topic': 'entity.v1', 'fields': {'entity_id': str(i)}, 'sha256': str(i), 'bytes': 1} for i in (1, 2)]
        runtimes = ['python', 'typescript', 'csharp']
        state = {'subscribers': {name: {'runtime': name, 'topics': ['entity.v1', 'entity.v2'], 'pending': []} for name in runtimes},
                 'publications': [{k: v for k, v in record.items() if k != 'fields'} | {'recipients': runtimes} for record in published],
                 'acknowledgements': [{'subscriber': name, 'runtime': name, 'message_id': record['message_id'], 'topic': record['topic'], 'fields': record['fields']} for name in runtimes for record in published]}
        validate(state, published)
        mutations = [lambda s: s['acknowledgements'].pop(),
                     lambda s: s['acknowledgements'].append(copy.deepcopy(s['acknowledgements'][0])),
                     lambda s: s['acknowledgements'].reverse(),
                     lambda s: s['acknowledgements'][0].update(fields={'entity_id': 'wrong'}),
                     lambda s: s['publications'][0].update(recipients=['python']),
                     lambda s: s['publications'][0].update(sha256='wrong'),
                     lambda s: s['acknowledgements'][0].update(topic='entity.v2')]
        for mutate in mutations:
            broken = copy.deepcopy(state); mutate(broken)
            with self.assertRaises(RuntimeError):
                validate(broken, published)


if __name__ == '__main__':
    unittest.main()
