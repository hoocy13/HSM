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
from itertools import combinations
import math
from .models import Drug, MedicationRecord

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
        """获取预警药品列表（支持动态阈值和智能采购建议）"""
        import math
        today = date.today()
        expiry_threshold = today + timedelta(days=30)
        
        # 动态阈值：基于过去30天的平均消耗量计算安全库存天数
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        # 获取所有药品的消耗统计
        drug_consumption = MedicationRecord.objects.filter(
            record_time__gte=thirty_days_ago
        ).values('drug').annotate(
            total_consumption=Sum('quantity')
        )
        
        consumption_dict = {item['drug']: item['total_consumption'] for item in drug_consumption}
        
        # 计算每日消耗量（用于计算标准差）
        drug_consumption_daily = defaultdict(list)
        for record in MedicationRecord.objects.filter(record_time__gte=thirty_days_ago):
            drug_consumption_daily[record.drug_id].append(record.quantity)
        
        # 计算每个药品的动态阈值（使用时间序列分析公式）
        warning_drugs_list = []
        procurement_list = []  # 智能采购清单
        
        for drug in Drug.objects.all():
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
        """创建用药记录时自动扣除库存（效期熔断机制）"""
        drug = serializer.validated_data['drug']
        quantity = serializer.validated_data['quantity']
        
        # 效期熔断机制：检查药品是否已过期
        today = date.today()
        if drug.expiry_date and drug.expiry_date < today:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({
                'drug': f'该药品已过期（有效期：{drug.expiry_date}），无法出库'
            })
        
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
        queryset = User.objects.select_related('profile').all()
        username = self.request.query_params.get('username', None)
        if username is not None:
            queryset = queryset.filter(username__icontains=username)
        return queryset
    
    def update(self, request, *args, **kwargs):
        """更新用户，确保返回最新的角色信息"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        # 重新从数据库获取用户实例（使用select_related确保profile被加载）
        updated_instance = User.objects.select_related('profile').get(pk=instance.pk)
        
        # 重新序列化以获取最新的角色信息
        updated_serializer = self.get_serializer(updated_instance)
        return Response(updated_serializer.data)


class DashboardViewSet(viewsets.ViewSet):
    """数据看板视图集"""
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['get'], url_path='stats')
    def stats(self, request):
        """获取今日核心指标"""
        today = timezone.now().date()
        today_start = timezone.make_aware(datetime.combine(today, datetime.min.time()))
        
        # 总金额（所有药品的成本价格总和）
        from django.db.models import Sum as DSum
        total_amount = Drug.objects.aggregate(
            total=DSum('cost_price')
        )['total'] or 0
        # 转换为浮点数并保留2位小数
        total_amount = float(total_amount) if total_amount else 0.0
        
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
            'total_amount': round(total_amount, 2),
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
        """获取药品关联关系图数据（节点大小+连线粗细+临床建议）"""
        try:
            # 获取最近90天的记录
            start_date = timezone.now().date() - timedelta(days=90)
            
            # 按prescription_id分组，获取同一处方下的所有药品
            records = MedicationRecord.objects.filter(
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
            for record in MedicationRecord.objects.all():
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
        drug_consumption = MedicationRecord.objects.filter(
            record_time__gte=thirty_days_ago
        ).values('drug').annotate(
            total_consumption=Sum('quantity')
        )
        
        consumption_dict = {item['drug']: item['total_consumption'] for item in drug_consumption}
        
        # 计算每日消耗量（用于计算标准差）
        drug_consumption_daily = defaultdict(list)
        for record in MedicationRecord.objects.filter(record_time__gte=thirty_days_ago):
            drug_consumption_daily[record.drug_id].append(record.quantity)
        
        low_stock_drugs = []
        for drug in Drug.objects.all():
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
        records = MedicationRecord.objects.filter(
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
            records = MedicationRecord.objects.filter(
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
    
