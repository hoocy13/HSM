"""单一药品库存事件时间轴（重建在库数量变化）。"""
from django.utils import timezone

from ..models import Drug, InventoryAdjustment, MedicationRecord


def build_stock_trend(drug_id: int):
    drug = Drug.objects.get(pk=drug_id)
    events = []

    for adj in InventoryAdjustment.objects.filter(drug_id=drug_id).order_by('created_at'):
        events.append(
            {'t': timezone.localtime(adj.created_at), 'delta': adj.quantity_change, 'reason': adj.reason or '库存调整'}
        )

    for mr in MedicationRecord.objects.filter(drug_id=drug_id):
        if mr.status == 'ACTIVE' and mr.dispense_status == 'dispensed':
            events.append(
                {'t': timezone.localtime(mr.record_time), 'delta': -mr.quantity, 'reason': '处方出库'}
            )
        elif mr.status == 'CANCELLED' and mr.cancelled_at:
            events.append(
                {'t': timezone.localtime(mr.cancelled_at), 'delta': mr.quantity, 'reason': '撤销处方'}
            )

    events.sort(key=lambda x: x['t'])
    total_delta = sum(e['delta'] for e in events)
    running = drug.stock - total_delta
    history = []
    for e in events:
        running += e['delta']
        history.append({
            'date': e['t'].strftime('%Y-%m-%d %H:%M:%S'),
            'stock': running,
            'change': e['delta'],
            'reason': e['reason'],
        })

    return {'history': history}
