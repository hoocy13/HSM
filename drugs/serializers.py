from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Drug, MedicationRecord
from datetime import date, timedelta


class DrugSerializer(serializers.ModelSerializer):
    """药品序列化器"""
    is_expiring_soon = serializers.SerializerMethodField()
    is_low_stock = serializers.SerializerMethodField()
    
    class Meta:
        model = Drug
        fields = ['id', 'name', 'category', 'stock', 'cost_price', 'expiry_date', 'is_expiring_soon', 'is_low_stock', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_is_expiring_soon(self, obj):
        """检查是否即将过期（30天内）"""
        return obj.is_expiring_soon(days=30)
    
    def get_is_low_stock(self, obj):
        """检查是否库存不足（低于50件）"""
        return obj.is_low_stock(threshold=50)
    
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
        choices=[('admin', '管理员'), ('doctor', '医生'), ('patient', '患者')],
        write_only=True,
        required=False,
        help_text="用户角色（仅更新时使用）"
    )
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 'role_write']
        read_only_fields = ['id']
    
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
        # 提取role_write字段（如果存在）
        role = validated_data.pop('role_write', None)
        # 也支持role字段（向后兼容）
        if role is None:
            role = validated_data.pop('role', None)
        
        # 更新用户基本信息
        instance = super().update(instance, validated_data)
        
        # 更新用户角色
        if role is not None:
            from .models import UserProfile
            profile, created = UserProfile.objects.get_or_create(user=instance)
            profile.role = role
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
        choices=[('admin', '管理员'), ('doctor', '医生'), ('patient', '患者')],
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
    
    class Meta:
        model = MedicationRecord
        fields = ['id', 'user', 'drug', 'drug_name', 'prescription_id', 'quantity', 'record_time', 'notes']
        read_only_fields = ['id', 'record_time']
    
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
