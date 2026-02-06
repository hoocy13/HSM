from rest_framework import serializers
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Drug, MedicationRecord, InventoryAdjustment, Announcement, Policy, OperationLog
from datetime import date, timedelta


class DrugSerializer(serializers.ModelSerializer):
    """药品序列化器"""
    is_expiring_soon = serializers.SerializerMethodField()
    is_low_stock = serializers.SerializerMethodField()
    
    class Meta:
        model = Drug
        fields = [
            'id', 'name', 'category', 'stock', 'cost_price', 'expiry_date',
            'min_stock', 'expiry_warning_days', 'department',
            'is_expiring_soon', 'is_low_stock', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_is_expiring_soon(self, obj):
        return obj.is_expiring_soon()

    def get_is_low_stock(self, obj):
        return obj.is_low_stock()
    
    def validate_stock(self, value):
        """验证库存不能为负数"""
        if value < 0:
            raise serializers.ValidationError("库存不能为负数")
        return value


class DrugStockUpdateSerializer(serializers.Serializer):
    """药品入库序列化器"""
    quantity = serializers.IntegerField(min_value=1, help_text="入库数量")
    
    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("入库数量必须大于0")
        return value


class UserSerializer(serializers.ModelSerializer):
    """用户序列化器"""
    role = serializers.SerializerMethodField()
    role_write = serializers.ChoiceField(
        choices=[('admin', '管理员'), ('doctor', '医生'), ('pharmacist', '药剂师'), ('patient', '患者')],
        write_only=True,
        required=False,
        help_text="用户角色（仅更新时使用）"
    )
    avatar = serializers.SerializerMethodField()
    department = serializers.SerializerMethodField()
    avatar_write = serializers.URLField(write_only=True, required=False, allow_blank=True)
    department_write = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'role_write', 'avatar', 'department', 'avatar_write', 'department_write',
        ]
        read_only_fields = ['id']

    def get_avatar(self, obj):
        try:
            if hasattr(obj, 'profile') and obj.profile:
                return obj.profile.avatar or ''
        except Exception:
            pass
        return ''

    def get_department(self, obj):
        try:
            if hasattr(obj, 'profile') and obj.profile:
                return obj.profile.department or ''
        except Exception:
            pass
        return ''
    
    def get_role(self, obj):
        """获取用户角色"""
        try:
            # 尝试从profile获取角色
            if hasattr(obj, 'profile'):
                return obj.profile.role
            # 如果没有profile，尝试从数据库获取
            from .models import UserProfile
            profile = UserProfile.objects.filter(user=obj).first()
            if profile:
                return profile.role
        except Exception:
            pass
        return 'patient'  # 默认角色
    
    def update(self, instance, validated_data):
        """更新用户信息，包括角色"""
        role = validated_data.pop('role_write', None)
        if role is None:
            role = validated_data.pop('role', None)
        avatar = validated_data.pop('avatar_write', None)
        department = validated_data.pop('department_write', None)

        instance = super().update(instance, validated_data)

        if role is not None or avatar is not None or department is not None:
            from .models import UserProfile
            profile, created = UserProfile.objects.get_or_create(user=instance)
            if role is not None:
                profile.role = role
            if avatar is not None:
                profile.avatar = avatar
            if department is not None:
                profile.department = department
            profile.save()
        
        # 刷新实例以获取最新的profile（必须在更新profile之后）
        instance.refresh_from_db()
        # 清除缓存，强制重新加载profile关系
        if hasattr(instance, '_state'):
            if 'profile' in getattr(instance._state, 'fields_cache', {}):
                del instance._state.fields_cache['profile']
        
        return instance


class UserRegisterSerializer(serializers.ModelSerializer):
    """用户注册序列化器"""
    password = serializers.CharField(write_only=True, min_length=6, help_text="密码（至少6位）")
    password_confirm = serializers.CharField(write_only=True, min_length=6, help_text="确认密码")
    role = serializers.ChoiceField(
        choices=[('admin', '管理员'), ('doctor', '医生'), ('pharmacist', '药剂师'), ('patient', '患者')],
        default='patient',
        write_only=True,
        help_text="用户角色"
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password_confirm', 'first_name', 'last_name', 'role']
    
    def validate(self, attrs):
        """验证密码是否一致"""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': '两次输入的密码不一致'
            })
        return attrs
    
    def create(self, validated_data):
        """创建用户"""
        validated_data.pop('password_confirm')
        role = validated_data.pop('role', 'patient')
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        
        # 创建用户角色
        from .models import UserProfile
        UserProfile.objects.get_or_create(user=user, defaults={'role': role})
        
        return user


class MedicationRecordSerializer(serializers.ModelSerializer):
    """用药记录序列化器"""
    user = UserSerializer(read_only=True)
    drug_name = serializers.CharField(source='drug.name', read_only=True)
    prescribed_by = UserSerializer(read_only=True)
    record_time = serializers.DateTimeField(required=False, default=timezone.now)

    class Meta:
        model = MedicationRecord
        fields = [
            'id', 'user', 'drug', 'drug_name', 'prescription_id', 'quantity',
            'record_time', 'notes', 'status', 'prescribed_by',
            'disease_name', 'department', 'cancelled_at',
        ]
        read_only_fields = ['id', 'status', 'department', 'cancelled_at']
    
    def validate_prescription_id(self, value):
        """验证处方号"""
        # 如果为空，允许（会自动生成）
        if not value:
            return ''
        # 如果提供了处方号，确保格式正确
        if len(value) > 50:
            raise serializers.ValidationError("处方号长度不能超过50个字符")
        return value
    
    def validate_quantity(self, value):
        """验证领药数量"""
        if value <= 0:
            raise serializers.ValidationError("领药数量必须大于0")
        return value
    
    def validate(self, attrs):
        """验证库存是否充足"""
        drug = attrs.get('drug')
        quantity = attrs.get('quantity')
        
        if drug and quantity:
            if drug.stock < quantity:
                raise serializers.ValidationError({
                    'quantity': f'库存不足，当前库存：{drug.stock}件'
                })
        return attrs


class InventoryAdjustmentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryAdjustment
        fields = ['drug', 'quantity_change', 'reason']


class InventoryAdjustmentSerializer(serializers.ModelSerializer):
    drug_name = serializers.CharField(source='drug.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = InventoryAdjustment
        fields = ['id', 'drug', 'drug_name', 'quantity_change', 'reason', 'created_by', 'created_by_name', 'created_at']
        read_only_fields = ['id', 'created_by', 'created_at']


class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = ['id', 'title', 'content', 'is_active', 'created_at']


class PolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = Policy
        fields = ['id', 'title', 'content', 'is_active', 'created_at']


class OperationLogSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True, allow_null=True)

    class Meta:
        model = OperationLog
        fields = ['id', 'user', 'username', 'action_type', 'target_type', 'target_id', 'detail', 'created_at']
        read_only_fields = ['id', 'user', 'username', 'action_type', 'target_type', 'target_id', 'detail', 'created_at']
