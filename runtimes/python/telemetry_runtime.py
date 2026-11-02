"""Small telemetry consumer/producer using canonical generated bindings."""
import base64
import json
import sys
from telemetry.vehicle_pb2 import VehicleTelemetry


def evaluate(request):
    entity = VehicleTelemetry.FromString(base64.b64decode(request['payload'], validate=True))
    sample = VehicleTelemetry(vehicle_id=request['vehicle_id'], speed_mps=request['speed'])
    fields = {'vehicle_id': entity.vehicle_id, 'speed_mps': entity.speed_mps}
    return {'fields': fields, 'speeding': entity.speed_mps > 30.0,
            'constructed_payload': base64.b64encode(sample.SerializeToString()).decode()}


def run():
    print(json.dumps([evaluate(request) for request in json.load(sys.stdin)]))
