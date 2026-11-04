"""Stock producer/consumer; JSON quantities are canonical decimal strings."""
import base64
import json
import sys
from inventory.item_pb2 import STOCK_STATE_UNSPECIFIED, StockItem


def evaluate(request):
    entity = StockItem.FromString(base64.b64decode(request['payload'], validate=True))
    sample = StockItem(sku=request['sku'], quantity=int(request['quantity']))
    fields = {'sku': entity.sku, 'quantity': str(entity.quantity)}
    return {'fields': fields, 'in_stock': entity.quantity > 0 and entity.state == STOCK_STATE_UNSPECIFIED,
            'constructed_payload': base64.b64encode(sample.SerializeToString()).decode()}


def run():
    print(json.dumps([evaluate(request) for request in json.load(sys.stdin)]))
