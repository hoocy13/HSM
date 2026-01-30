from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.utils import timezone
from django.db.models import Sum, Count, Q, F
from django.db.models.functions import TruncDate
from datetime import date, timedelta, datetime
from collections import defaultdict
from .models import Drug, MedicationRecord
from .serializers import (
    DrugSerializer, 
    DrugStockUpdateSerializer,
    MedicationRecordSerializer,
    UserSerializer,
    UserRegisterSerializer
)


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
        return queryset
    
    @action(detail=True, methods=['post'], url_path='stock-in')
    def stock_in(self, request, pk=None):
        """药品入库功能"""
        drug = self.get_object()
        serializer = DrugStockUpdateSerializer(data=request.data)
        
        if serializer.is_valid():
            quantity = serializer.validated_data['quantity']
            drug.stock += quantity
            drug.save()
            
            return Response({
                'message': f'成功入库 {quantity} 件',
                'drug': DrugSerializer(drug).data
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'], url_path='warnings')
    def warnings(self, request):
        """获取预警药品列表（有效期少于30天或库存低于50件）"""
        today = date.today()
        expiry_threshold = today + timedelta(days=30)
        
        # 筛选即将过期的药品
        expiring_soon = Drug.objects.filter(
            expiry_date__lte=expiry_threshold,
            expiry_date__gte=today
        )
        
        # 筛选库存不足的药品
        low_stock = Drug.objects.filter(stock__lt=50)
        
        # 合并去重
        warning_drugs = (expiring_soon | low_stock).distinct()
        
        serializer = self.get_serializer(warning_drugs, many=True)
        return Response({
            'count': warning_drugs.count(),
            'results': serializer.data
        })


class MedicationRecordViewSet(viewsets.ModelViewSet):
    """用药记录视图集"""
    queryset = MedicationRecord.objects.all()
    serializer_class = MedicationRecordSerializer
    permission_classes = [AllowAny]  # 暂时允许所有用户
    
    def get_queryset(self):
        """获取查询集，支持按用户和药品筛选"""
        queryset = MedicationRecord.objects.all()
        user_id = self.request.query_params.get('user', None)
        drug_id = self.request.query_params.get('drug', None)
        
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        if drug_id:
            queryset = queryset.filter(drug_id=drug_id)
        
        return queryset
    
    def perform_create(self, serializer):
        """创建用药记录时自动扣除库存"""
        drug = serializer.validated_data['drug']
        quantity = serializer.validated_data['quantity']
        
        # 检查库存
        if drug.stock < quantity:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({
                'quantity': f'库存不足，当前库存：{drug.stock}件'
            })
        
        # 如果没有指定用户，使用当前登录用户
        if not serializer.validated_data.get('user'):
            if self.request.user.is_authenticated:
                serializer.save(user=self.request.user)
            else:
                # 如果没有登录，使用默认用户（开发环境）
                default_user = User.objects.first()
                if default_user:
                    serializer.save(user=default_user)
                else:
                    serializer.save()
        else:
            serializer.save()
        
        # 扣除库存
        drug.stock -= quantity
        drug.save()


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
    
    @action(detail=False, methods=['post'], url_path='register')
    def register(self, request):
        """用户注册"""
        serializer = UserRegisterSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                'message': '注册成功',
                'user': UserSerializer(user).data
            }, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserViewSet(viewsets.ModelViewSet):
    """用户视图集（支持增删改查）"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]  # 暂时允许所有用户
    
    def get_queryset(self):
        """获取查询集，支持按用户名搜索"""
        queryset = User.objects.all()
        username = self.request.query_params.get('username', None)
        if username is not None:
            queryset = queryset.filter(username__icontains=username)
        return queryset


class DashboardViewSet(viewsets.ViewSet):
    """数据看板视图集"""
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['get'], url_path='stats')
    def stats(self, request):
        """获取今日核心指标"""
        today = timezone.now().date()
        today_start = timezone.make_aware(datetime.combine(today, datetime.min.time()))
        
        # 总金额（基于用药记录，假设每个药品平均价格，这里用数量*10作为示例）
        total_amount = MedicationRecord.objects.filter(
            record_time__date=today
        ).aggregate(
            total=Sum('quantity')
        )['total'] or 0
        total_amount = total_amount * 10  # 假设单价10元
        
        # 待发药处方（今日创建的用药记录数）
        pending_prescriptions = MedicationRecord.objects.filter(
            record_time__date=today
        ).count()
        
        # 今日新增预警（今日过期或库存不足的药品数）
        expiring_drugs = Drug.objects.filter(
            expiry_date__lte=today + timedelta(days=30),
            expiry_date__gte=today
        ).count()
        low_stock_drugs = Drug.objects.filter(stock__lt=50).count()
        today_warnings = expiring_drugs + low_stock_drugs
        
        # 周转率（今日出库量 / 总库存）
        today_consumption = MedicationRecord.objects.filter(
            record_time__date=today
        ).aggregate(
            total=Sum('quantity')
        )['total'] or 0
        total_stock = Drug.objects.aggregate(total=Sum('stock'))['total'] or 1
        turnover_rate = round((today_consumption / total_stock) * 100, 2) if total_stock > 0 else 0
        
        return Response({
            'total_amount': total_amount,
            'pending_prescriptions': pending_prescriptions,
            'today_warnings': today_warnings,
            'turnover_rate': turnover_rate
        })
    
    @action(detail=False, methods=['get'], url_path='consumption-trend')
    def consumption_trend(self, request):
        """获取消耗趋势预测数据"""
        # 获取最近30天的数据
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
        
        # 按日期聚合用药记录
        records = MedicationRecord.objects.filter(
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
        """获取药品关联矩阵数据"""
        # 获取所有用药记录，按用户和时间分组
        # 找出经常一起开出的药品组合
        
        # 获取最近90天的记录
        start_date = timezone.now().date() - timedelta(days=90)
        
        # 按用户和日期分组，找出同一天同一用户开出的药品
        records = MedicationRecord.objects.filter(
            record_time__date__gte=start_date
        ).select_related('drug', 'user').order_by('user', 'record_time')
        
        # 构建药品共现矩阵
        drug_pairs = defaultdict(int)
        drug_counts = defaultdict(int)
        
        # 按用户和时间窗口（同一天）分组
        user_date_groups = defaultdict(set)
        for record in records:
            date_key = record.record_time.date()
            user_date_groups[(record.user.id, date_key)].add(record.drug.id)
        
        # 统计药品共现
        for drug_ids in user_date_groups.values():
            drug_list = list(drug_ids)
            # 统计每个药品的出现次数
            for drug_id in drug_list:
                drug_counts[drug_id] += 1
            # 统计药品对的出现次数
            for i in range(len(drug_list)):
                for j in range(i + 1, len(drug_list)):
                    pair = tuple(sorted([drug_list[i], drug_list[j]]))
                    drug_pairs[pair] += 1
        
        # 获取药品名称映射
        drug_names = {drug.id: drug.name for drug in Drug.objects.all()}
        
        # 构建关联数据（只返回共现次数>=2的药品对）
        correlations = []
        for (drug1_id, drug2_id), count in drug_pairs.items():
            if count >= 2:  # 至少共现2次
                correlations.append({
                    'drug1': drug_names.get(drug1_id, f'Drug {drug1_id}'),
                    'drug2': drug_names.get(drug2_id, f'Drug {drug2_id}'),
                    'count': count,
                    'drug1_id': drug1_id,
                    'drug2_id': drug2_id
                })
        
        # 按共现次数排序
        correlations.sort(key=lambda x: x['count'], reverse=True)
        
        return Response({
            'correlations': correlations[:50]  # 返回前50个最相关的组合
        })