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
        fields = ['id', 'name', 'stock', 'expiry_date', 'is_expiring_soon', 'is_low_stock', 'created_at', 'updated_at']
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
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = ['id']


class UserRegisterSerializer(serializers.ModelSerializer):
    """用户注册序列化器"""
    password = serializers.CharField(write_only=True, min_length=6, help_text="密码（至少6位）")
    password_confirm = serializers.CharField(write_only=True, min_length=6, help_text="确认密码")
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password_confirm', 'first_name', 'last_name']
    
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
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        return user


class MedicationRecordSerializer(serializers.ModelSerializer):
    """用药记录序列化器"""
    user = UserSerializer(read_only=True)
    drug_name = serializers.CharField(source='drug.name', read_only=True)
    
    class Meta:
        model = MedicationRecord
        fields = ['id', 'user', 'drug', 'drug_name', 'quantity', 'record_time', 'notes']
        read_only_fields = ['id', 'record_time']
    
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
