"""预警中心：库存/效期变化时写入 Alert，Dashboard 优先读表。"""
from datetime import timedelta

from django.utils import timezone

from ..models import Alert, Drug


def maybe_alerts_for_drug(drug: Drug, department=''):
    """
    库存或效期相关变更后调用：必要时插入 LOW_STOCK / EXPIRY 预警。
    """
    today = timezone.now().date()
    dept = (department or getattr(drug, 'department', '') or '')[:100]

    if drug.stock <= (drug.min_stock or 0):
        Alert.objects.create(
            type='LOW_STOCK',
            level='warning',
            content=f'{drug.name} 库存 {drug.stock}，已低于安全库存 {drug.min_stock}。',
            target_role='pharmacist',
            department=dept,
            target_type='drug',
            target_id=drug.id,
        )
        Alert.objects.create(
            type='LOW_STOCK',
            level='warning',
            content=f'{drug.name} 库存不足，当前 {drug.stock}。',
            target_role='admin',
            department='',
            target_type='drug',
            target_id=drug.id,
        )

    days = drug.expiry_warning_days or 30
    if drug.expiry_date and today <= drug.expiry_date <= today + timedelta(days=days):
        Alert.objects.create(
            type='EXPIRY',
            level='warning',
            content=f'{drug.name} 将在 {days} 天内过期（{drug.expiry_date}）。',
            target_role='pharmacist',
            department=dept,
            target_type='drug',
            target_id=drug.id,
        )


def maybe_disease_trend_alert(prefix_message: str, department=''):
    """疾病趋势类提醒（可由业务在统计后写一条）。"""
    Alert.objects.create(
        type='DISEASE_TREND',
        level='info',
        content=prefix_message[:500],
        target_role='doctor',
        department=(department or '')[:100],
        target_type='',
        target_id=0,
    )


def maybe_disease_spike_alert(disease_name: str, department: str = ''):
    """近7天相对前7天记录数明显上升时写入 DISEASE_TREND。"""
    if not (disease_name or '').strip():
        return
    from ..models import MedicationRecord
    from datetime import timedelta

    today = timezone.now().date()
    cur_start = today - timedelta(days=7)
    prev_start = today - timedelta(days=14)
    base = MedicationRecord.objects.filter(
        status='ACTIVE', dispense_status='dispensed', disease_name=disease_name.strip()
    )
    if department:
        base = base.filter(department=department)
    cur = base.filter(record_time__date__gte=cur_start).count()
    prev = base.filter(record_time__date__gte=prev_start, record_time__date__lt=cur_start).count()
    if prev == 0 and cur >= 3:
        maybe_disease_trend_alert(f'「{disease_name}」相关用药近期增多，请关注。', department)
    elif prev > 0 and cur >= prev * 1.5 and cur >= 3:
        maybe_disease_trend_alert(f'「{disease_name}」相关用药较前一周上升。', department)
