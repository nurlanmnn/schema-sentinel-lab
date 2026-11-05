"""Stock producer/consumer; JSON quantities are canonical decimal strings."""
import base64
import json
import sys
from inventory.item_pb2 import STOCK_STATE_QUARANTINED, STOCK_STATE_UNSPECIFIED, StockItem


def evaluate(request):
    entity = StockItem.FromString(base64.b64decode(request['payload'], validate=True))
    sample = StockItem(sku=request['sku'], quantity=int(request['quantity']),
                       display_labels=request.get('display_labels', []),
                       warehouse=request.get('warehouse', ''), drop_zone=request.get('drop_zone', ''))
    fields = {'sku': entity.sku, 'quantity': str(entity.quantity)}
    if 'display_labels' in request:
        fields['display_labels'] = list(entity.display_labels)
    if request.get('include_route'):
        fields['warehouse'] = entity.warehouse
        fields['drop_zone'] = entity.drop_zone
    if request.get('include_state'):
        fields['state_label'] = {
            STOCK_STATE_UNSPECIFIED: 'UNSPECIFIED',
            STOCK_STATE_QUARANTINED: 'QUARANTINED',
        }.get(entity.state, 'UNKNOWN')
    return {'fields': fields, 'in_stock': entity.quantity > 0 and entity.state == STOCK_STATE_UNSPECIFIED,
            'constructed_payload': base64.b64encode(sample.SerializeToString()).decode()}


def run():
    print(json.dumps([evaluate(request) for request in json.load(sys.stdin)]))
