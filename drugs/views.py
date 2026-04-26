from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.utils import timezone
from django.db import transaction
from django.db.models import Sum, Count, Q, F, Case, When, Value, IntegerField
from django.db.models.functions import TruncDate
from datetime import date, timedelta, datetime
from collections import defaultdict
from itertools import combinations
import math
from .models import Drug, MedicationRecord, InventoryAdjustment, OperationLog, Alert, Announcement
from .permissions import _role, IsAdminOrPharmacist, IsAdmin
from .dashboard_service import build_home_payload, build_trends_payload, build_recommendations_payload, _scope_med_qs

# 临床建议字典（药品联用注意事项）
CLINICAL_ADVICE = {
    ('antibiotic', 'antiviral'): '注意胃肠道副作用，建议饭后服用',
    ('antipyretic', 'cold'): '注意肝肾功能，避免长期联用',
    ('cardiovascular', 'diabetes'): '注意血压和血糖监测',
    ('antibiotic', 'vitamin'): '抗生素可能影响维生素吸收',
    ('antipyretic', 'digestive'): '注意胃肠道刺激，建议间隔服用',
}

def get_clinical_advice(drug1_category, drug2_category):
    """获取药品联用临床建议"""
    key1 = (drug1_category, drug2_category)
    key2 = (drug2_category, drug1_category)
    return CLINICAL_ADVICE.get(key1) or CLINICAL_ADVICE.get(key2) or '请咨询医生确认联用安全性'
from .serializers import (
    DrugSerializer,
    DrugStockUpdateSerializer,
    MedicationRecordSerializer,
    UserSerializer,
    UserCreateSerializer,
    InventoryAdjustmentCreateSerializer,
    InventoryAdjustmentSerializer,
    OperationLogSerializer,
    AnnouncementSerializer,
)


def active_medication_qs():
    return MedicationRecord.objects.filter(status='ACTIVE')


def scoped_active_med(request):
    return _scope_med_qs(active_medication_qs(), request)


def fulfilled_medication_qs():
    """已发药（已扣库存）的用药记录，用于消耗统计与图表。"""
    return MedicationRecord.objects.filter(status='ACTIVE', dispense_status='dispensed')


def scoped_fulfilled_med(request):
    return _scope_med_qs(fulfilled_medication_qs(), request)


def dashboard_scoped_drugs(request):
    qs = Drug.objects.all()
    r = _role(request.user) if request.user.is_authenticated else None
    if r == 'pharmacist':
        try:
            dept = (request.user.profile.department or '').strip()
        except Exception:
            dept = ''
        if dept:
            qs = qs.filter(Q(department=dept) | Q(department=''))
    return qs


class DrugViewSet(viewsets.ModelViewSet):
    """
    药品视图集
    提供增删改查功能：
    - list: 获取药品列表
    - create: 创建新药品
    - retrieve: 获取单个药品详情
    - update: 更新药品（完整更新）
    - partial_update: 更新药品（部分更新）
    - destroy: 删除药品
    - stock_in: 药品入库
    - warnings: 获取预警药品列表
    """
    queryset = Drug.objects.all()
    serializer_class = DrugSerializer
    permission_classes = [AllowAny]  # 暂时允许所有用户，后续可以改为 IsAuthenticated
    
    def get_queryset(self):
        """获取查询集，支持按名称搜索和预警筛选"""
        queryset = Drug.objects.all()
        name = self.request.query_params.get('name', None)
        if name is not None:
            queryset = queryset.filter(name__icontains=name)
        r = _role(self.request.user) if self.request.user.is_authenticated else None
        if r == 'pharmacist':
            try:
                dept = (self.request.user.profile.department or '').strip()
            except Exception:
                dept = ''
            if dept:
                queryset = queryset.filter(Q(department=dept) | Q(department=''))
        today = timezone.now().date()
        exp_cutoff = today + timedelta(days=30)
        queryset = queryset.annotate(
            _alert_rank=Case(
                When(expiry_date__isnull=False, expiry_date__lte=exp_cutoff, then=Value(2)),
                When(stock__lte=F('min_stock'), then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            )
        )
        sort_mode = (self.request.query_params.get('alert_sort') or '').lower()
        if sort_mode == 'desc':
            queryset = queryset.order_by('-_alert_rank', '-id')
        elif sort_mode == 'asc':
            queryset = queryset.order_by('_alert_rank', '-id')
        return queryset

    def perform_update(self, serializer):
        from .services.log_service import log_operation
        from .services.alert_service import maybe_alerts_for_drug

        with transaction.atomic():
            d = serializer.save()
            if self.request.user.is_authenticated:
                log_operation(
                    user=self.request.user,
                    action_type='UPDATE_DRUG',
                    target_type='drug',
                    target_id=d.id,
                    detail=f'更新药品 {d.name}',
                )
            d2 = Drug.objects.select_for_update().get(pk=d.pk)
            maybe_alerts_for_drug(d2, d2.department or '')

    @action(detail=True, methods=['get'], url_path='stock-trend')
    def stock_trend(self, request, pk=None):
        from .services.stock_trend_service import build_stock_trend

        return Response(build_stock_trend(int(pk)))
    
    @action(
        detail=True,
        methods=['post'],
        url_path='stock-in',
        permission_classes=[IsAuthenticated, IsAdminOrPharmacist],
    )
    def stock_in(self, request, pk=None):
        """药品入库功能（记入 InventoryAdjustment 流水）"""
        drug = self.get_object()
        serializer = DrugStockUpdateSerializer(data=request.data)

        if serializer.is_valid():
            from .services.log_service import log_operation
            from .services.alert_service import maybe_alerts_for_drug

            quantity = serializer.validated_data['quantity']
            with transaction.atomic():
                d = Drug.objects.select_for_update().get(pk=drug.pk)
                d.stock += quantity
                d.save()
                InventoryAdjustment.objects.create(
                    drug=d,
                    quantity_change=quantity,
                    reason='入库',
                    created_by=request.user,
                )
                log_operation(
                    user=request.user,
                    action_type='STOCK_IN',
                    target_type='drug',
                    target_id=d.id,
                    detail=f'入库 {quantity} 件',
                )
                d = Drug.objects.select_for_update().get(pk=d.pk)
                maybe_alerts_for_drug(d, d.department or '')
                Alert.objects.create(
                    type='ARRIVAL',
                    level='info',
                    content=f'{d.name} 入库 {quantity} 件',
                    target_role='doctor',
                    department=d.department or '',
                    target_type='drug',
                    target_id=d.id,
                )
            d.refresh_from_db()
            return Response({
                'message': f'成功入库 {quantity} 件',
                'drug': DrugSerializer(d).data
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'], url_path='warnings')
    def warnings(self, request):
        """获取预警药品列表（支持动态阈值和智能采购建议）"""
        import math
        today = date.today()
        expiry_threshold = today + timedelta(days=30)
        
        # 动态阈值：基于过去30天的平均消耗量计算安全库存天数
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        # 获取所有药品的消耗统计
        drug_consumption = scoped_fulfilled_med(request).filter(
            record_time__gte=thirty_days_ago
        ).values('drug').annotate(
            total_consumption=Sum('quantity')
        )
        
        consumption_dict = {item['drug']: item['total_consumption'] for item in drug_consumption}
        
        # 计算每日消耗量（用于计算标准差）
        drug_consumption_daily = defaultdict(list)
        for record in scoped_fulfilled_med(request).filter(record_time__gte=thirty_days_ago):
            drug_consumption_daily[record.drug_id].append(record.quantity)
        
        # 计算每个药品的动态阈值（使用时间序列分析公式）
        warning_drugs_list = []
        procurement_list = []  # 智能采购清单
        
        drug_qs = self.get_queryset()
        for drug in Drug.objects.filter(pk__in=drug_qs.values_list('id', flat=True)):
            is_warning = False
            warning_reasons = []
            suggested_purchase = 0
            
            # 检查是否已过期
            if drug.expiry_date and drug.expiry_date < today:
                is_warning = True
                warning_reasons.append('已过期')
            
            # 检查是否即将过期
            elif drug.expiry_date and drug.expiry_date <= expiry_threshold and drug.expiry_date >= today:
                is_warning = True
                warning_reasons.append('即将过期')
            
            # 动态阈值检查（使用时间序列分析公式）
            avg_daily_consumption = consumption_dict.get(drug.id, 0) / 30.0 if consumption_dict.get(drug.id, 0) > 0 else 0
            
            # SS = (Avg_usage × L) + (z × σ × √L)
            L = 7  # 采购周期（天）
            z = 1.65  # 95%服务水平系数
            
            # 计算标准差
            daily_consumptions = drug_consumption_daily.get(drug.id, [])
            if len(daily_consumptions) > 1:
                mean_cons = sum(daily_consumptions) / len(daily_consumptions)
                variance = sum((x - mean_cons) ** 2 for x in daily_consumptions) / len(daily_consumptions)
                sigma = math.sqrt(variance) if variance > 0 else 0
            else:
                sigma = 0
            
            # 计算安全库存
            safety_stock = int((avg_daily_consumption * L) + (z * sigma * math.sqrt(L))) if avg_daily_consumption > 0 else 50
            
            # 最大库存上限（安全库存的2倍）
            max_stock = safety_stock * 2 if safety_stock > 0 else 100
            
            if drug.stock < safety_stock:
                is_warning = True
                warning_reasons.append('库存不足')
                # 智能采购建议：建议量 = (最大库存上限 - 当前库存) + 在途订单（这里假设为0）
                in_transit = 0  # 在途订单数量（可以从订单系统获取）
                suggested_purchase = max(0, (max_stock - drug.stock) + in_transit)
                
                # 添加到采购清单
                procurement_list.append({
                    'drug_id': drug.id,
                    'drug_name': drug.name,
                    'current_stock': drug.stock,
                    'safety_stock': safety_stock,
                    'max_stock': max_stock,
                    'suggested_purchase': suggested_purchase,
                    'cost_price': float(drug.cost_price),
                    'estimated_cost': float(drug.cost_price) * suggested_purchase
                })
            
            if is_warning:
                drug_data = self.get_serializer(drug).data
                drug_data['warning_reasons'] = warning_reasons
                drug_data['safety_stock'] = safety_stock
                drug_data['avg_daily_consumption'] = round(avg_daily_consumption, 2)
                drug_data['suggested_purchase'] = suggested_purchase
                warning_drugs_list.append(drug_data)
        
        # 计算采购清单总成本
        total_procurement_cost = sum(item['estimated_cost'] for item in procurement_list)
        
        return Response({
            'count': len(warning_drugs_list),
            'results': warning_drugs_list,
            'procurement_list': procurement_list,  # 智能采购清单
            'total_procurement_cost': round(total_procurement_cost, 2)
        })


class MedicationRecordViewSet(viewsets.ModelViewSet):
    """用药记录：医师开具处方（待发药，不扣库存）；药剂师审批发药后扣库存。"""
    queryset = MedicationRecord.objects.all()
    serializer_class = MedicationRecordSerializer
    permission_classes = [AllowAny]

    def get_permissions(self):
        if self.action in [
            'create', 'destroy', 'cancel', 'dispense', 'undo_dispense', 'reject_pending', 'department_users',
        ]:
            return [IsAuthenticated()]
        return [AllowAny()]

    def get_queryset(self):
        queryset = MedicationRecord.objects.all().order_by('-record_time', '-id')
        user_id = self.request.query_params.get('user', None)
        drug_id = self.request.query_params.get('drug', None)
        date_from = self.request.query_params.get('date_from', None)
        date_to = self.request.query_params.get('date_to', None)
        drug_name = (self.request.query_params.get('drug_name') or '').strip()
        dispense_status = (self.request.query_params.get('dispense_status') or '').strip()
        dispensed_by = (self.request.query_params.get('dispensed_by') or '').strip()
        dispensed_from = self.request.query_params.get('dispensed_from', None)
        dispensed_to = self.request.query_params.get('dispensed_to', None)

        r = _role(self.request.user) if self.request.user.is_authenticated else None
        if r in ('doctor', 'pharmacist'):
            try:
                dept = (self.request.user.profile.department or '').strip()
            except Exception:
                dept = ''
            if dept:
                queryset = queryset.filter(department=dept)

        if user_id:
            queryset = queryset.filter(user_id=user_id)
        if drug_id:
            queryset = queryset.filter(drug_id=drug_id)
        if drug_name:
            queryset = queryset.filter(drug__name__icontains=drug_name)
        if date_from:
            queryset = queryset.filter(record_time__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(record_time__date__lte=date_to)
        if dispense_status in ('pending', 'dispensed'):
            queryset = queryset.filter(dispense_status=dispense_status)
        if dispensed_by:
            if dispensed_by.isdigit():
                queryset = queryset.filter(dispensed_by_id=int(dispensed_by))
            else:
                queryset = queryset.filter(dispensed_by__username__icontains=dispensed_by)
        if dispensed_from:
            queryset = queryset.filter(dispensed_at__date__gte=dispensed_from)
        if dispensed_to:
            queryset = queryset.filter(dispensed_at__date__lte=dispensed_to)

        return queryset

    def perform_create(self, serializer):
        """仅医师可开具处方：待发药，不扣库存；每张处方仅一种药品。"""
        from .services.log_service import log_operation
        from rest_framework.exceptions import PermissionDenied, ValidationError

        role = _role(self.request.user) if self.request.user.is_authenticated else None
        if role != 'doctor':
            raise PermissionDenied('仅医师可开具处方。')

        drug = serializer.validated_data['drug']
        quantity = serializer.validated_data['quantity']
        disease_name = (serializer.validated_data.get('disease_name') or '').strip()
        rx = (serializer.validated_data.get('prescription_id') or '').strip()
        if not rx:
            raise ValidationError({'prescription_id': '开具处方必须带处方号；请使用系统「开具处方」入口。'})
        if active_medication_qs().filter(prescription_id=rx).exists():
            raise ValidationError({
                'prescription_id': '每张处方仅允许开具一种药品（一条记录），不可在同一处方号下添加第二种药品。',
            })

        patient_user_id = serializer.validated_data.pop('patient_user_id', None)
        target_user = self.request.user
        if patient_user_id is not None:
            try:
                target_user = User.objects.get(pk=patient_user_id)
            except User.DoesNotExist:
                raise ValidationError({'patient_user_id': '患者用户不存在'})

        today = date.today()
        if drug.expiry_date and drug.expiry_date < today:
            raise ValidationError({
                'drug': f'该药品已过期（有效期：{drug.expiry_date}），不可开处方'
            })

        try:
            dept = (self.request.user.profile.department or '').strip()
        except Exception:
            dept = ''

        with transaction.atomic():
            d = Drug.objects.select_for_update().get(pk=drug.pk)
            if d.expiry_date and d.expiry_date < today:
                raise ValidationError({
                    'drug': f'该药品已过期（有效期：{d.expiry_date}），不可开处方'
                })
            if d.stock < quantity:
                raise ValidationError({
                    'quantity': f'库存不足，当前库存：{d.stock}件'
                })

            instance = serializer.save(
                user=target_user,
                department=dept,
                disease_name=disease_name,
                prescribed_by=self.request.user,
                dispense_status='pending',
            )
            log_operation(
                user=self.request.user,
                action_type='CREATE_PRESCRIPTION',
                target_type='prescription',
                target_id=instance.id,
                detail=f'处方 {instance.prescription_id} 待发药 患者:{target_user.username}(id={target_user.id}) '
                f'药品 {d.name} 数量 {quantity} 疾病:{disease_name or "-"}',
            )

    def destroy(self, request, *args, **kwargs):
        from rest_framework.exceptions import PermissionDenied as PD

        instance = self.get_object()
        role = _role(request.user)
        if role not in ('admin', 'doctor'):
            raise PD('无权删除')
        if role == 'doctor' and instance.prescribed_by_id != request.user.id:
            raise PD('无权删除')
        with transaction.atomic():
            if instance.status == 'ACTIVE' and instance.dispense_status == 'dispensed':
                Drug.objects.filter(pk=instance.drug_id).update(stock=F('stock') + instance.quantity)
            instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], url_path='department-users', permission_classes=[IsAuthenticated])
    def department_users(self, request):
        """开具处方时选择患者：本科室用户列表（不含管理员）。"""
        from rest_framework.exceptions import PermissionDenied as PD

        if _role(request.user) != 'doctor':
            raise PD('仅医师可查询')
        try:
            dept = (request.user.profile.department or '').strip()
        except Exception:
            dept = ''
        qs = User.objects.select_related('profile').exclude(profile__role='admin')
        if dept:
            qs = qs.filter(profile__department=dept)
        results = [{'id': u.id, 'username': u.username} for u in qs.order_by('id')[:500]]
        return Response({'results': results})

    @action(detail=True, methods=['post'], url_path='dispense', permission_classes=[IsAuthenticated])
    def dispense(self, request, pk=None):
        """药剂师同意发药：核对患者用户ID后扣减库存。"""
        from .services.log_service import log_operation
        from .services.alert_service import maybe_alerts_for_drug, maybe_disease_spike_alert
        from rest_framework.exceptions import PermissionDenied as PD, ValidationError

        if _role(request.user) != 'pharmacist':
            raise PD('仅药剂师可审批发药')
        confirm_uid = request.data.get('confirm_user_id')
        if confirm_uid is not None and str(confirm_uid).strip() == '':
            confirm_uid = None
        if confirm_uid is not None:
            try:
                confirm_uid = int(confirm_uid)
            except (TypeError, ValueError):
                raise ValidationError({'confirm_user_id': '患者用户ID须为数字'})

        with transaction.atomic():
            record = MedicationRecord.objects.select_for_update().select_related('drug', 'user').get(pk=pk)
            if record.status != 'ACTIVE':
                return Response({'error': '该记录已作废'}, status=status.HTTP_400_BAD_REQUEST)
            if record.dispense_status != 'pending':
                return Response({'error': '该处方已发药或不可重复发药'}, status=status.HTTP_400_BAD_REQUEST)
            try:
                pdept = (request.user.profile.department or '').strip()
            except Exception:
                pdept = ''
            if pdept and (record.department or '').strip() and (record.department or '').strip() != pdept:
                raise PD('非本科室处方，无权发药')
            if confirm_uid is not None and confirm_uid != record.user_id:
                raise ValidationError({'confirm_user_id': f'与处方患者不一致（处方用户ID为 {record.user_id}）'})

            d = Drug.objects.select_for_update().get(pk=record.drug_id)
            today = date.today()
            if d.expiry_date and d.expiry_date < today:
                return Response({'error': '药品已过期，无法发药'}, status=status.HTTP_400_BAD_REQUEST)
            if d.stock < record.quantity:
                return Response(
                    {'error': f'库存不足，当前库存 {d.stock}，需 {record.quantity}'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            d.stock -= record.quantity
            d.save()
            now = timezone.now()
            record.dispense_status = 'dispensed'
            record.dispensed_at = now
            record.dispensed_by = request.user
            record.save()
            log_operation(
                user=request.user,
                action_type='APPROVE_DISPENSE',
                target_type='prescription',
                target_id=record.id,
                detail=f'发药 记录#{record.id} 处方 {record.prescription_id} 患者 {record.user.username}(id={record.user_id}) '
                f'{d.name} x{record.quantity}',
            )
            d2 = Drug.objects.select_for_update().get(pk=d.pk)
            maybe_alerts_for_drug(d2, (record.department or d2.department or ''))

        maybe_disease_spike_alert(record.disease_name, record.department or '')
        out = MedicationRecordSerializer(record, context={'request': request}).data
        return Response(out)

    @action(detail=True, methods=['post'], url_path='reject-pending', permission_classes=[IsAuthenticated])
    def reject_pending(self, request, pk=None):
        """药剂师拒绝待发药处方（患者未取药等），不扣库存。"""
        from .services.log_service import log_operation
        from rest_framework.exceptions import PermissionDenied as PD

        if _role(request.user) != 'pharmacist':
            raise PD('仅药剂师可操作')
        with transaction.atomic():
            record = MedicationRecord.objects.select_for_update().get(pk=pk)
            if record.status != 'ACTIVE' or record.dispense_status != 'pending':
                return Response({'error': '仅可拒绝「待发药」记录'}, status=status.HTTP_400_BAD_REQUEST)
            try:
                pdept = (request.user.profile.department or '').strip()
            except Exception:
                pdept = ''
            if pdept and (record.department or '').strip() and (record.department or '').strip() != pdept:
                raise PD('非本科室处方')
            now = timezone.now()
            record.status = 'CANCELLED'
            record.cancelled_at = now
            record.save()
            log_operation(
                user=request.user,
                action_type='REJECT_DISPENSE',
                target_type='prescription',
                target_id=record.id,
                detail=f'拒绝待发药 记录#{record.id} 处方 {record.prescription_id}',
            )
        return Response({'message': '已拒绝', 'id': record.id})

    @action(detail=True, methods=['post'], url_path='undo-dispense', permission_classes=[IsAuthenticated])
    def undo_dispense(self, request, pk=None):
        """撤销发药：回补库存并退回待发药，便于点错后重审。"""
        from .services.log_service import log_operation
        from .services.alert_service import maybe_alerts_for_drug
        from rest_framework.exceptions import PermissionDenied as PD

        if _role(request.user) != 'pharmacist':
            raise PD('仅药剂师可撤销发药')

        with transaction.atomic():
            record = MedicationRecord.objects.select_for_update().select_related('drug').get(pk=pk)
            if record.status != 'ACTIVE':
                return Response({'error': '该记录已作废，无法撤销发药'}, status=status.HTTP_400_BAD_REQUEST)
            if record.dispense_status != 'dispensed':
                return Response({'error': '仅已发药记录可撤销发药'}, status=status.HTTP_400_BAD_REQUEST)
            try:
                pdept = (request.user.profile.department or '').strip()
            except Exception:
                pdept = ''
            if pdept and (record.department or '').strip() and (record.department or '').strip() != pdept:
                raise PD('非本科室处方，无权撤销发药')

            d = Drug.objects.select_for_update().get(pk=record.drug_id)
            d.stock += record.quantity
            d.save()
            record.dispense_status = 'pending'
            record.dispensed_at = None
            record.dispensed_by = None
            record.save()
            log_operation(
                user=request.user,
                action_type='REJECT_DISPENSE',
                target_type='prescription',
                target_id=record.id,
                detail=f'撤销发药 记录#{record.id} 处方 {record.prescription_id}',
            )
            d2 = Drug.objects.select_for_update().get(pk=d.pk)
            maybe_alerts_for_drug(d2, (record.department or d2.department or ''))

        out = MedicationRecordSerializer(record, context={'request': request}).data
        return Response(out)

    @action(detail=True, methods=['post'], url_path='cancel', permission_classes=[IsAuthenticated])
    def cancel(self, request, pk=None):
        """撤销处方：待发药不涉库存；已发药回滚库存。"""
        record = self.get_object()
        if record.status != 'ACTIVE':
            return Response({'error': '该记录已作废'}, status=status.HTTP_400_BAD_REQUEST)

        role = _role(request.user)
        can = role == 'admin'
        if not can and record.prescribed_by_id and record.prescribed_by_id == request.user.id:
            can = True
        if not can and role == 'pharmacist' and record.dispense_status == 'pending':
            try:
                pdept = (request.user.profile.department or '').strip()
            except Exception:
                pdept = ''
            rdept = (record.department or '').strip()
            if pdept and rdept and pdept == rdept:
                can = True
        if not can:
            return Response({'error': '无权撤销该处方'}, status=status.HTTP_403_FORBIDDEN)

        from .services.log_service import log_operation

        with transaction.atomic():
            if record.prescription_id:
                qs = MedicationRecord.objects.select_for_update().filter(
                    prescription_id=record.prescription_id,
                    status='ACTIVE',
                )
            else:
                qs = MedicationRecord.objects.select_for_update().filter(pk=record.pk, status='ACTIVE')

            for r in qs:
                if r.dispense_status == 'dispensed':
                    Drug.objects.filter(pk=r.drug_id).update(stock=F('stock') + r.quantity)
            now = timezone.now()
            qs.update(status='CANCELLED', cancelled_at=now)
            log_operation(
                user=request.user,
                action_type='CANCEL_PRESCRIPTION',
                target_type='prescription',
                target_id=record.id,
                detail=f'撤销处方 {record.prescription_id or record.id}',
            )

        return Response({'message': '处方已撤销', 'prescription_id': record.prescription_id or None})


class InventoryAdjustmentViewSet(viewsets.ModelViewSet):
    """库存盘点 / 损溢录入"""
    queryset = InventoryAdjustment.objects.select_related('drug', 'created_by').order_by('-created_at')
    serializer_class = InventoryAdjustmentSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get('only_in') == '1':
            qs = qs.filter(quantity_change__gt=0)
        r = _role(self.request.user) if self.request.user.is_authenticated else None
        if r == 'pharmacist':
            try:
                dept = (self.request.user.profile.department or '').strip()
            except Exception:
                dept = ''
            if dept:
                qs = qs.filter(Q(drug__department=dept) | Q(drug__department=''))
        return qs

    def get_serializer_class(self):
        if self.action == 'create':
            return InventoryAdjustmentCreateSerializer
        return InventoryAdjustmentSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated(), IsAdminOrPharmacist()]
        return [AllowAny()]

    def perform_create(self, serializer):
        from .services.log_service import log_operation
        from .services.alert_service import maybe_alerts_for_drug

        drug = serializer.validated_data['drug']
        qty = serializer.validated_data['quantity_change']
        reason = serializer.validated_data.get('reason', '')
        from rest_framework.exceptions import ValidationError

        with transaction.atomic():
            d = Drug.objects.select_for_update().get(pk=drug.pk)
            if d.stock + qty < 0:
                raise ValidationError({'quantity_change': '调整后库存不能为负数'})
            d.stock += qty
            d.save()
            serializer.save(created_by=self.request.user if self.request.user.is_authenticated else None)
            log_operation(
                user=self.request.user if self.request.user.is_authenticated else None,
                action_type='INVENTORY_ADJUST',
                target_type='drug',
                target_id=d.id,
                detail=f'{reason} 变动{qty:+d}',
            )
            d2 = Drug.objects.select_for_update().get(pk=d.pk)
            maybe_alerts_for_drug(d2, d2.department or '')


class AuthViewSet(viewsets.ViewSet):
    """用户认证视图集"""
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['post'], url_path='login')
    def login(self, request):
        """用户登录（返回简单的 token，后续可以改为 JWT）"""
        username = request.data.get('username')
        password = request.data.get('password')
        
        if not username or not password:
            return Response({
                'error': '用户名和密码不能为空'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user = authenticate(username=username, password=password)
        
        if user:
            # 简单的 token 返回（实际应该使用 JWT）
            return Response({
                'token': f'simple_token_{user.id}',  # 临时方案
                'user': UserSerializer(user).data,
                'message': '登录成功'
            })
        else:
            return Response({
                'error': '用户名或密码错误'
            }, status=status.HTTP_401_UNAUTHORIZED)
    
    @action(detail=False, methods=['post'], url_path='logout')
    def logout(self, request):
        """用户登出"""
        return Response({
            'message': '登出成功'
        })
    
class UserViewSet(viewsets.ModelViewSet):
    """用户视图集（支持增删改查）"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer

    def perform_create(self, serializer):
        from .services.log_service import log_operation

        user = serializer.save()
        log_operation(
            user=self.request.user,
            action_type='CREATE_USER',
            target_type='user',
            target_id=user.id,
            detail=f'管理员创建用户 {user.username}',
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        user = User.objects.select_related('profile').get(pk=serializer.instance.pk)
        return Response(UserSerializer(user, context=self.get_serializer_context()).data, status=status.HTTP_201_CREATED)

    def get_queryset(self):
        """获取查询集，支持按用户名/角色/科室筛选"""
        queryset = User.objects.select_related('profile').all()
        username = (self.request.query_params.get('username') or '').strip()
        role = (self.request.query_params.get('role') or '').strip()
        department = (self.request.query_params.get('department') or '').strip()
        if username:
            queryset = queryset.filter(username__icontains=username)
        if role in ('admin', 'doctor', 'pharmacist'):
            queryset = queryset.filter(profile__role=role)
        if department:
            queryset = queryset.filter(profile__department__icontains=department)
        return queryset

    def update(self, request, *args, **kwargs):
        """更新用户，确保返回最新的角色信息"""
        from .models import UserProfile
        from .services.log_service import log_operation

        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        old_profile = UserProfile.objects.filter(user=instance).first()
        old_role = old_profile.role if old_profile else None
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            self.perform_update(serializer)
            instance.refresh_from_db()
            new_profile = UserProfile.objects.filter(user=instance).first()
            new_role = new_profile.role if new_profile else None
            if old_role != new_role and request.user.is_authenticated:
                log_operation(
                    user=request.user,
                    action_type='UPDATE_USER_ROLE',
                    target_type='user',
                    target_id=instance.id,
                    detail=f'{old_role}->{new_role}',
                )
        updated_instance = User.objects.select_related('profile').get(pk=instance.pk)
        updated_serializer = self.get_serializer(updated_instance)
        return Response(updated_serializer.data)

    def destroy(self, request, *args, **kwargs):
        """兼容旧删除入口：改为停用账号，保留员工资料。"""
        return self.deactivate(request, pk=kwargs.get('pk'))

    @action(detail=True, methods=['post'], url_path='deactivate', permission_classes=[IsAuthenticated, IsAdmin])
    def deactivate(self, request, pk=None):
        """停用员工账号（不可登录，资料保留）。"""
        from .services.log_service import log_operation

        user = self.get_object()
        if user.id == request.user.id:
            return Response({'error': '不可停用当前登录管理员账号'}, status=status.HTTP_400_BAD_REQUEST)
        if not user.is_active:
            return Response({'message': '账号已是停用状态'})
        user.is_active = False
        user.save(update_fields=['is_active'])
        log_operation(
            user=request.user,
            action_type='UPDATE_USER_ROLE',
            target_type='user',
            target_id=user.id,
            detail=f'停用账号 {user.username}',
        )
        data = self.get_serializer(user).data
        return Response({'message': '已停用', 'user': data})

    @action(detail=True, methods=['post'], url_path='activate', permission_classes=[IsAuthenticated, IsAdmin])
    def activate(self, request, pk=None):
        """启用员工账号。"""
        from .services.log_service import log_operation

        user = self.get_object()
        if user.is_active:
            return Response({'message': '账号已是启用状态'})
        user.is_active = True
        user.save(update_fields=['is_active'])
        log_operation(
            user=request.user,
            action_type='UPDATE_USER_ROLE',
            target_type='user',
            target_id=user.id,
            detail=f'启用账号 {user.username}',
        )
        data = self.get_serializer(user).data
        return Response({'message': '已启用', 'user': data})


class DashboardViewSet(viewsets.ViewSet):
    """数据看板视图集"""
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['get'], url_path='stats')
    def stats(self, request):
        """数据概览：用药总次数、活跃药品数、低库存、预警数量（不含金额/待发药等）"""
        today = timezone.now().date()

        # 支持 days=30 或 date_from/date_to，默认近30天（不改变返回结构）
        start_date = None
        end_date = None
        try:
            qp = request.query_params
            if qp.get('date_from') and qp.get('date_to'):
                try:
                    start_date = datetime.strptime(qp.get('date_from'), '%Y-%m-%d').date()
                    end_date = datetime.strptime(qp.get('date_to'), '%Y-%m-%d').date()
                    if start_date > end_date:
                        start_date, end_date = end_date, start_date
                except Exception:
                    start_date = None
                    end_date = None
            elif qp.get('days'):
                try:
                    days = int(qp.get('days'))
                    days = max(1, min(days, 365))
                    end_date = today
                    start_date = today - timedelta(days=days)
                except Exception:
                    start_date = None
                    end_date = None
            else:
                end_date = today
                start_date = today - timedelta(days=30)
        except Exception:
            end_date = today
            start_date = today - timedelta(days=30)

        med = scoped_fulfilled_med(request)
        if start_date and end_date:
            med = med.filter(record_time__date__gte=start_date, record_time__date__lte=end_date)
        total_medication_count = med.count()
        active_drug_count = Drug.objects.filter(
            id__in=med.values_list('drug_id', flat=True).distinct()
        ).count()
        low_stock_count = dashboard_scoped_drugs(request).filter(stock__lte=F('min_stock')).count()

        expiring_count = 0
        for d in dashboard_scoped_drugs(request).exclude(expiry_date__isnull=True):
            days = d.expiry_warning_days or 30
            if today <= d.expiry_date <= today + timedelta(days=days):
                expiring_count += 1
        warning_count = low_stock_count + expiring_count

        return Response({
            'total_medication_count': total_medication_count,
            'active_drug_count': active_drug_count,
            'low_stock_count': low_stock_count,
            'warning_count': warning_count,
        })

    def list(self, request):
        """首页 Dashboard：公告、政策、按角色拆分的提醒"""
        role = _role(request.user) if request.user.is_authenticated else None
        return Response(build_home_payload(role or 'doctor', request))

    @action(detail=False, methods=['get'], url_path='trends')
    def trends(self, request):
        """数据趋势：处方量折线 + 药品共现矩阵 + 疾病趋势"""
        return Response(build_trends_payload(request))

    @action(detail=False, methods=['get'], url_path='recommendations')
    def recommendations(self, request):
        return Response(build_recommendations_payload(request))
    
    @action(detail=False, methods=['get'], url_path='consumption-trend')
    def consumption_trend(self, request):
        """获取消耗趋势预测数据"""
        # 获取最近30天的数据
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
        
        # 按日期聚合用药记录
        records = scoped_fulfilled_med(request).filter(
            record_time__date__gte=start_date,
            record_time__date__lte=end_date
        ).annotate(
            date=TruncDate('record_time')
        ).values('date').annotate(
            total=Sum('quantity')
        ).order_by('date')
        
        # 构建日期和消耗量列表
        dates = []
        actual_consumption = []
        consumption_dict = {item['date']: item['total'] for item in records}
        
        current_date = start_date
        while current_date <= end_date:
            dates.append(current_date.strftime('%Y-%m-%d'))
            actual_consumption.append(consumption_dict.get(current_date, 0))
            current_date += timedelta(days=1)
        
        # 简单的移动平均预测（未来7天）
        # 使用最近7天的平均值作为预测
        recent_avg = sum(actual_consumption[-7:]) / 7 if len(actual_consumption) >= 7 else (sum(actual_consumption) / len(actual_consumption) if actual_consumption else 0)
        
        # 预测未来7天
        forecast_dates = []
        forecast_consumption = []
        for i in range(1, 8):
            forecast_date = end_date + timedelta(days=i)
            forecast_dates.append(forecast_date.strftime('%Y-%m-%d'))
            forecast_consumption.append(round(recent_avg, 2))
        
        return Response({
            'dates': dates,
            'actual': actual_consumption,
            'forecast_dates': forecast_dates,
            'forecast': forecast_consumption
        })
    
    @action(detail=False, methods=['get'], url_path='drug-correlation')
    def drug_correlation(self, request):
        """获取药品关联关系图数据（节点大小+连线粗细+临床建议）"""
        try:
            # 获取最近90天的记录
            start_date = timezone.now().date() - timedelta(days=90)
            
            # 按prescription_id分组，获取同一处方下的所有药品
            records = scoped_fulfilled_med(request).filter(
                record_time__date__gte=start_date
            ).exclude(prescription_id='').select_related('drug').values('prescription_id', 'drug_id').distinct()
            
            # 按prescription_id分组
            prescription_drugs = defaultdict(set)
            for record in records:
                prescription_id = record['prescription_id']
                drug_id = record['drug_id']
                prescription_drugs[prescription_id].add(drug_id)
            
            # 统计每个药品的总消耗量（用于节点大小）
            drug_total_consumption = defaultdict(int)
            for record in scoped_fulfilled_med(request).all():
                drug_total_consumption[record.drug_id] += record.quantity
            
            # 使用itertools.combinations统计药品共现
            drug_pairs = defaultdict(int)
            
            for prescription_id, drug_ids in prescription_drugs.items():
                drug_list = sorted(list(drug_ids))
                if len(drug_list) >= 2:
                    for drug1_id, drug2_id in combinations(drug_list, 2):
                        pair = (drug1_id, drug2_id)
                        drug_pairs[pair] += 1
            
            # 获取药品信息映射
            drugs_info = {drug.id: {'name': drug.name, 'category': drug.category} for drug in Drug.objects.all()}
            
            # 构建关系图数据：节点和边
            nodes = []
            edges = []
            node_ids = set()
            
            # 添加节点（圆点大小代表总消耗量）
            max_consumption = max(drug_total_consumption.values()) if drug_total_consumption else 1
            for drug_id, consumption in drug_total_consumption.items():
                if drug_id in drugs_info:
                    node_ids.add(drug_id)
                    # 节点大小：最小20，最大100，根据消耗量比例
                    node_size = 20 + (consumption / max_consumption) * 80 if max_consumption > 0 else 20
                    nodes.append({
                        'id': drug_id,
                        'name': drugs_info[drug_id]['name'],
                        'category': drugs_info[drug_id]['category'],
                        'value': consumption,
                        'symbolSize': round(node_size, 2)
                    })
            
            # 添加边（连线粗细代表关联频次）
            max_count = max(drug_pairs.values()) if drug_pairs else 1
            for (drug1_id, drug2_id), count in drug_pairs.items():
                if count >= 1 and drug1_id in node_ids and drug2_id in node_ids:  # 降低阈值，返回count >= 1的关联对
                    # 连线粗细：最小1，最大10，根据count比例
                    line_width = 1 + (count / max_count) * 9 if max_count > 1 else 1
                    
                    # 获取临床建议
                    drug1_category = drugs_info.get(drug1_id, {}).get('category', 'other')
                    drug2_category = drugs_info.get(drug2_id, {}).get('category', 'other')
                    clinical_advice = get_clinical_advice(drug1_category, drug2_category)
                    
                    edges.append({
                        'source': drug1_id,
                        'target': drug2_id,
                        'value': count,
                        'lineStyle': {
                            'width': round(line_width, 2)
                        },
                        'label': {
                            'show': True,
                            'formatter': f'{count}次'
                        },
                        'clinical_advice': clinical_advice
                    })
            
            return Response({
                'nodes': nodes,
                'links': edges
            })
        except Exception as e:
            return Response({
                'nodes': [],
                'links': [],
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'], url_path='low-stock-top10')
    def low_stock_top10(self, request):
        """获取库存紧缺Top10（引入缺口程度概念）"""
        # 计算每个药品的库存紧缺程度（基于动态阈值）
        thirty_days_ago = timezone.now() - timedelta(days=30)
        drug_consumption = scoped_fulfilled_med(request).filter(
            record_time__gte=thirty_days_ago
        ).values('drug').annotate(
            total_consumption=Sum('quantity')
        )
        
        consumption_dict = {item['drug']: item['total_consumption'] for item in drug_consumption}
        
        # 计算每日消耗量（用于计算标准差）
        drug_consumption_daily = defaultdict(list)
        for record in scoped_fulfilled_med(request).filter(record_time__gte=thirty_days_ago):
            drug_consumption_daily[record.drug_id].append(record.quantity)
        
        low_stock_drugs = []
        for drug in dashboard_scoped_drugs(request):
            avg_daily_consumption = consumption_dict.get(drug.id, 0) / 30.0 if consumption_dict.get(drug.id, 0) > 0 else 0
            
            # 动态阈值算法：SS = (Avg_usage × L) + (z × σ × √L)
            # L = 采购周期（7天），z = 服务水平系数（1.65对应95%服务水平），σ = 标准差
            L = 7  # 采购周期（天）
            z = 1.65  # 95%服务水平系数
            
            # 计算标准差
            daily_consumptions = drug_consumption_daily.get(drug.id, [])
            if len(daily_consumptions) > 1:
                mean_cons = sum(daily_consumptions) / len(daily_consumptions)
                variance = sum((x - mean_cons) ** 2 for x in daily_consumptions) / len(daily_consumptions)
                sigma = math.sqrt(variance) if variance > 0 else 0
            else:
                sigma = 0
            
            # 计算安全库存
            safety_stock = int((avg_daily_consumption * L) + (z * sigma * math.sqrt(L))) if avg_daily_consumption > 0 else 50
            
            # 计算缺口程度：差值百分比 = (安全库存 - 当前库存) / 安全库存 × 100%
            if safety_stock > 0:
                gap = safety_stock - drug.stock
                gap_percentage = (gap / safety_stock) * 100 if safety_stock > 0 else 0
                
                # 确定严重程度：0-30%黄色，30-60%橙色，60%+红色
                if gap_percentage <= 30:
                    severity = 'low'  # 黄色
                elif gap_percentage <= 60:
                    severity = 'medium'  # 橙色
                else:
                    severity = 'high'  # 红色
                
                low_stock_drugs.append({
                    'id': drug.id,
                    'name': drug.name,
                    'stock': drug.stock,
                    'safety_stock': safety_stock,
                    'gap': gap,
                    'gap_percentage': round(gap_percentage, 2),
                    'severity': severity,
                    'suggested_purchase': max(0, safety_stock - drug.stock + int(safety_stock * 0.2))
                })
        
        # 按缺口百分比排序（越大越紧缺）
        low_stock_drugs.sort(key=lambda x: x['gap_percentage'], reverse=True)
        
        return Response({
            'results': low_stock_drugs[:10]
        })
    
    @action(detail=False, methods=['get'], url_path='expiry-distribution')
    def expiry_distribution(self, request):
        """获取过期预警分布（旭日图数据：内圈状态+外圈分类）"""
        today = date.today()
        thirty_days_later = today + timedelta(days=30)
        
        # 内圈：已过期、快过期、安全
        expired_drugs = Drug.objects.filter(expiry_date__lt=today)
        expiring_soon_drugs = Drug.objects.filter(
            expiry_date__gte=today,
            expiry_date__lte=thirty_days_later
        )
        safe_drugs = Drug.objects.filter(
            Q(expiry_date__gt=thirty_days_later) | Q(expiry_date__isnull=True)
        )
        
        # 构建旭日图数据
        sunburst_data = []
        
        # 已过期（内圈）
        expired_count = expired_drugs.count()
        if expired_count > 0:
            expired_item = {
                'name': '已过期',
                'value': expired_count,
                'children': []
            }
            # 外圈：按分类统计
            expired_by_category = expired_drugs.values('category').annotate(count=Count('id'))
            for item in expired_by_category:
                expired_item['children'].append({
                    'name': dict(Drug.CATEGORY_CHOICES).get(item['category'], '其他'),
                    'value': item['count']
                })
            sunburst_data.append(expired_item)
        
        # 快过期（内圈）
        expiring_count = expiring_soon_drugs.count()
        if expiring_count > 0:
            expiring_item = {
                'name': '快过期',
                'value': expiring_count,
                'children': []
            }
            # 外圈：按分类统计
            expiring_by_category = expiring_soon_drugs.values('category').annotate(count=Count('id'))
            for item in expiring_by_category:
                expiring_item['children'].append({
                    'name': dict(Drug.CATEGORY_CHOICES).get(item['category'], '其他'),
                    'value': item['count']
                })
            sunburst_data.append(expiring_item)
        
        # 安全（内圈）
        safe_count = safe_drugs.count()
        if safe_count > 0:
            safe_item = {
                'name': '安全',
                'value': safe_count,
                'children': []
            }
            # 外圈：按分类统计
            safe_by_category = safe_drugs.values('category').annotate(count=Count('id'))
            for item in safe_by_category:
                safe_item['children'].append({
                    'name': dict(Drug.CATEGORY_CHOICES).get(item['category'], '其他'),
                    'value': item['count']
                })
            sunburst_data.append(safe_item)
        
        return Response({
            'data': sunburst_data,
            'summary': {
                'expired': expired_count,
                'expiring_soon': expiring_count,
                'safe': safe_count,
                'total': expired_count + expiring_count + safe_count
            }
        })
    
    @action(detail=False, methods=['get'], url_path='monthly-consumption')
    def monthly_consumption(self, request):
        """获取月度消耗趋势（按月汇总，不按分类）"""
        # 获取从2025年8月到现在的所有数据
        from datetime import datetime
        start_date = timezone.make_aware(datetime(2025, 8, 1)).date()
        end_date = timezone.now().date()
        
        # 按月聚合所有药品的消耗
        records = scoped_fulfilled_med(request).filter(
            record_time__date__gte=start_date,
            record_time__date__lte=end_date
        ).annotate(
            month=TruncDate('record_time', kind='month')
        ).values('month').annotate(
            total=Sum('quantity')
        ).order_by('month')
        
        # 生成所有月份
        current_month = start_date.replace(day=1)
        all_months = []
        month_data_dict = {}
        
        while current_month <= end_date:
            month_str = current_month.strftime('%Y-%m')
            all_months.append(month_str)
            month_data_dict[month_str] = 0
            if current_month.month == 12:
                current_month = current_month.replace(year=current_month.year + 1, month=1)
            else:
                current_month = current_month.replace(month=current_month.month + 1)
        
        # 填充数据
        for record in records:
            month_str = record['month'].strftime('%Y-%m')
            if month_str in month_data_dict:
                month_data_dict[month_str] = record['total']
        
        # 构建数据列表
        data_list = [month_data_dict.get(month, 0) for month in all_months]
        
        # 计算环比（本月 vs 上月）
        mom_growth = 0
        if len(data_list) >= 2:
            current_month_value = data_list[-1]
            last_month_value = data_list[-2]
            if last_month_value > 0:
                mom_growth = ((current_month_value - last_month_value) / last_month_value) * 100
            else:
                mom_growth = 0 if current_month_value == 0 else 100
        
        return Response({
            'months': all_months,
            'data': data_list,
            'mom_growth': round(mom_growth, 2),  # 环比增长率
            'total_consumption': sum(data_list)
        })
    
    @action(detail=False, methods=['get'], url_path='top5-correlated')
    def top5_correlated(self, request):
        """获取经常一起被开出的药品Top5（包含临床建议）"""
        try:
            # 获取最近90天的记录
            start_date = timezone.now().date() - timedelta(days=90)
            
            # 按prescription_id分组，获取同一处方下的所有药品
            records = scoped_fulfilled_med(request).filter(
                record_time__date__gte=start_date
            ).exclude(prescription_id='').select_related('drug').values('prescription_id', 'drug_id').distinct()
            
            # 按prescription_id分组
            prescription_drugs = defaultdict(set)
            for record in records:
                prescription_id = record['prescription_id']
                drug_id = record['drug_id']
                prescription_drugs[prescription_id].add(drug_id)
            
            # 使用itertools.combinations统计药品共现
            drug_pairs = defaultdict(int)
            
            for prescription_id, drug_ids in prescription_drugs.items():
                drug_list = sorted(list(drug_ids))
                if len(drug_list) >= 2:
                    for drug1_id, drug2_id in combinations(drug_list, 2):
                        pair = (drug1_id, drug2_id)
                        drug_pairs[pair] += 1
            
            # 获取药品信息映射
            drugs_info = {drug.id: {'name': drug.name, 'category': drug.category} for drug in Drug.objects.all()}
            
            # 构建关联数据（只返回count > 2的关联对）
            correlations = []
            for (drug1_id, drug2_id), count in drug_pairs.items():
                if count > 2:
                    drug1_info = drugs_info.get(drug1_id, {})
                    drug2_info = drugs_info.get(drug2_id, {})
                    
                    # 获取临床建议
                    clinical_advice = get_clinical_advice(
                        drug1_info.get('category', 'other'),
                        drug2_info.get('category', 'other')
                    )
                    
                    correlations.append({
                        'drug1': drug1_info.get('name', f'Drug {drug1_id}'),
                        'drug2': drug2_info.get('name', f'Drug {drug2_id}'),
                        'count': count,
                        'clinical_advice': clinical_advice
                    })
            
            # 按count降序排列，取Top5
            correlations.sort(key=lambda x: x['count'], reverse=True)
            
            return Response({
                'results': correlations[:5]
            })
        except Exception as e:
            return Response({
                'results': [],
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AnnouncementViewSet(viewsets.ModelViewSet):
    """
    系统公告管理：仅管理员。
    启用（is_active=true）的公告由工作台首页等接口读取展示。
    """
    queryset = Announcement.objects.all().order_by('-created_at')
    serializer_class = AnnouncementSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

    def perform_create(self, serializer):
        from .services.log_service import log_operation

        obj = serializer.save()
        log_operation(
            user=self.request.user,
            action_type='CREATE_ANNOUNCEMENT',
            target_type='announcement',
            target_id=obj.id,
            detail=f'发布公告：{obj.title[:80]}',
        )

    def perform_update(self, serializer):
        from .services.log_service import log_operation

        obj = serializer.save()
        log_operation(
            user=self.request.user,
            action_type='UPDATE_ANNOUNCEMENT',
            target_type='announcement',
            target_id=obj.id,
            detail=f'更新公告：{obj.title[:80]}',
        )

    def destroy(self, request, *args, **kwargs):
        from .services.log_service import log_operation

        instance = self.get_object()
        tid = instance.id
        title = (instance.title or '')[:80]
        log_operation(
            user=request.user,
            action_type='DELETE_ANNOUNCEMENT',
            target_type='announcement',
            target_id=tid,
            detail=f'删除公告：{title}',
        )
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


class OperationLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = OperationLog.objects.select_related('user').all()
    serializer_class = OperationLogSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

    def get_queryset(self):
        qs = super().get_queryset().order_by('-created_at')
        if at := self.request.query_params.get('action_type'):
            qs = qs.filter(action_type=at)
        uid = (self.request.query_params.get('user_id') or '').strip()
        if uid:
            if uid.isdigit():
                qs = qs.filter(user_id=int(uid))
            else:
                qs = qs.filter(user__username__icontains=uid)
        if df := self.request.query_params.get('date_from'):
            qs = qs.filter(created_at__date__gte=df)
        if dr := self.request.query_params.get('date_to'):
            qs = qs.filter(created_at__date__lte=dr)
        return qs

