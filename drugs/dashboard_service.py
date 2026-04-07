"""
Dashboard：公告、政策、预警（优先读 Alert 表）、趋势与推荐。
"""
from datetime import timedelta
from collections import defaultdict
from itertools import combinations

from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone

from .models import Drug, MedicationRecord, Announcement, Policy, Alert
from .permissions import _role


def _active_medication_qs():
    return MedicationRecord.objects.filter(status='ACTIVE')

def _parse_date(s: str):
    if not s:
        return None
    try:
        # Expect YYYY-MM-DD
        return timezone.datetime.strptime(s, '%Y-%m-%d').date()
    except Exception:
        return None


def _get_window_from_request(request, default_days=30):
    """
    支持 query:
      - days=30（默认）
      - date_from=YYYY-MM-DD & date_to=YYYY-MM-DD（包含 date_to 当天）
    """
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=default_days)
    if request is None:
        return start_date, end_date
    try:
        qp = request.query_params
    except Exception:
        return start_date, end_date

    df = _parse_date((qp.get('date_from') or '').strip())
    dt = _parse_date((qp.get('date_to') or '').strip())
    if df and dt:
        if df > dt:
            df, dt = dt, df
        return df, dt

    try:
        days = int(qp.get('days') or default_days)
        days = max(1, min(days, 365))
        start_date = end_date - timedelta(days=days)
    except Exception:
        pass
    return start_date, end_date


def _scope_med_qs(qs, request):
    """医师/药剂师按科室过滤用药记录；admin 不过滤。"""
    if request is None or not request.user.is_authenticated:
        return qs
    r = _role(request.user)
    if r == 'admin':
        return qs
    if r not in ('doctor', 'pharmacist'):
        return qs
    try:
        dept = (request.user.profile.department or '').strip()
    except Exception:
        dept = ''
    if not dept:
        return qs
    return qs.filter(department=dept)


def list_announcements():
    return list(
        Announcement.objects.filter(is_active=True).order_by('-created_at')[:20].values(
            'id', 'title', 'content', 'created_at'
        )
    )


def list_policies():
    return list(
        Policy.objects.filter(is_active=True).order_by('-created_at')[:20].values(
            'id', 'title', 'content', 'created_at'
        )
    )


def _serialize_alert_rows(rows):
    out = []
    for a in rows:
        out.append({
            'type': a.type,
            'message': a.content,
            'level': a.level,
            'is_read': a.is_read,
        })
    return out


def _alert_queryset_for_request(request):
    qs = Alert.objects.all()
    if request is None or not request.user.is_authenticated:
        return qs
    r = _role(request.user)
    if r == 'admin':
        return qs
    try:
        dept = (request.user.profile.department or '').strip()
    except Exception:
        dept = ''
    if dept:
        qs = qs.filter(Q(department='') | Q(department=dept))
    return qs


def build_home_payload(role, request=None):
    payload = {
        'announcements': list_announcements(),
        'policies': list_policies(),
        'doctor_alerts': [],
        'pharmacist_alerts': [],
    }
    base = _alert_queryset_for_request(request)

    if role == 'doctor':
        rows = base.filter(target_role__in=['doctor', 'admin']).order_by('-created_at')[:40]
        payload['doctor_alerts'] = _serialize_alert_rows(rows)
    elif role == 'pharmacist':
        rows = base.filter(target_role__in=['pharmacist', 'admin']).order_by('-created_at')[:40]
        payload['pharmacist_alerts'] = _serialize_alert_rows(rows)
    elif role == 'admin':
        drows = base.filter(target_role__in=['doctor', 'admin']).order_by('-created_at')[:30]
        prows = base.filter(target_role__in=['pharmacist', 'admin']).order_by('-created_at')[:30]
        payload['doctor_alerts'] = _serialize_alert_rows(drows)
        payload['pharmacist_alerts'] = _serialize_alert_rows(prows)
    return payload


def pharmacist_low_stock_alerts(threshold=None):
    """内部/脚本用：按 Drug.min_stock"""
    alerts = []
    for drug in Drug.objects.all().order_by('stock')[:30]:
        t = drug.min_stock if threshold is None else threshold
        if drug.stock <= t:
            alerts.append({
                'type': 'LOW_STOCK',
                'message': f"{drug.name} 库存 {drug.stock}，低于安全库存 {t}。",
                'drug_id': drug.id,
            })
    if not alerts:
        alerts.append({'type': 'LOW_STOCK', 'message': '当前暂无显著缺货品种。'})
    return alerts


def pharmacist_expiry_alerts(days=None):
    from datetime import date

    today = date.today()
    alerts = []
    for drug in Drug.objects.exclude(expiry_date__isnull=True).order_by('expiry_date'):
        ddays = drug.expiry_warning_days if days is None else days
        deadline = today + timedelta(days=ddays)
        if today <= drug.expiry_date <= deadline:
            alerts.append({
                'type': 'EXPIRY_WARNING',
                'message': f"{drug.name} 将在 {ddays} 天内过期（{drug.expiry_date}）。",
                'drug_id': drug.id,
            })
    if not alerts:
        alerts.append({'type': 'EXPIRY_WARNING', 'message': '暂无临近效期品种。'})
    return alerts


def build_trends_payload(request=None):
    """prescription_trend、drug_matrix 与原先一致；新增 disease_trend。"""
    start_date, end_date = _get_window_from_request(request, default_days=30)

    med = _active_medication_qs().filter(record_time__date__gte=start_date, record_time__date__lte=end_date)
    med = _scope_med_qs(med, request)

    rows = (
        med.annotate(d=TruncDate('record_time'))
        .values('d')
        .annotate(c=Count('id'))
        .order_by('d')
    )
    by_day = {r['d']: r['c'] for r in rows if r['d']}

    prescription_trend = []
    cur = start_date
    while cur <= end_date:
        prescription_trend.append({
            'date': cur.isoformat(),
            'count': int(by_day.get(cur, 0)),
        })
        cur += timedelta(days=1)

    top_ids = list(
        med.values('drug_id')
        .annotate(c=Count('id'))
        .order_by('-c')[:12]
        .values_list('drug_id', flat=True)
    )
    id_list = [i for i in top_ids if i]
    drugs = Drug.objects.in_bulk(id_list)
    labels = [drugs[i].name if i in drugs else str(i) for i in id_list]
    n = len(id_list)
    matrix = [[0 for _ in range(n)] for _ in range(n)]
    if n >= 2:
        rx_med = _active_medication_qs()
        rx_med = _scope_med_qs(rx_med, request)
        rx_map = defaultdict(set)
        for row in rx_med.exclude(prescription_id='').values('prescription_id', 'drug_id'):
            rx_map[row['prescription_id']].add(row['drug_id'])
        idx = {did: i for i, did in enumerate(id_list)}
        for drug_ids in rx_map.values():
            lst = [idx[d] for d in drug_ids if d in idx]
            for i in range(len(lst)):
                for j in range(i + 1, len(lst)):
                    a, b = lst[i], lst[j]
                    matrix[a][b] += 1
                    matrix[b][a] += 1

    drug_matrix = {'labels': labels, 'matrix': matrix}

    disease_rows = (
        med.exclude(disease_name='')
        .values('disease_name')
        .annotate(c=Count('id'))
        .order_by('-c')[:30]
    )
    disease_trend = [{'disease': r['disease_name'], 'count': r['c']} for r in disease_rows]

    return {
        'prescription_trend': prescription_trend,
        'drug_matrix': drug_matrix,
        'disease_trend': disease_trend,
    }


def build_recommendations_payload(request=None):
    rx_med = _active_medication_qs()
    rx_med = _scope_med_qs(rx_med, request)
    drug_ids = list(rx_med.exclude(prescription_id='').values_list('drug_id', flat=True).distinct())
    bulk = Drug.objects.in_bulk(drug_ids)
    id_name = {i: bulk[i].name for i in drug_ids if i in bulk}
    names_by_rx = defaultdict(set)
    for row in rx_med.exclude(prescription_id='').values('prescription_id', 'drug_id'):
        nm = id_name.get(row['drug_id'])
        if nm:
            names_by_rx[row['prescription_id']].add(nm)
    pair_counts = defaultdict(lambda: defaultdict(int))
    for drug_names in names_by_rx.values():
        ul = sorted(set(drug_names))
        for a, b in combinations(ul, 2):
            pair_counts[a][b] += 1
            pair_counts[b][a] += 1
    recommendations = []
    for drug_name, counter in pair_counts.items():
        top3 = [n for n, _ in sorted(counter.items(), key=lambda x: -x[1])[:3]]
        if top3:
            recommendations.append({'drug': drug_name, 'recommended_with': top3})
    recommendations.sort(
        key=lambda x: sum(pair_counts[x['drug']][w] for w in x['recommended_with']),
        reverse=True,
    )
    return {'recommendations': recommendations}
