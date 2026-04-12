from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.db.models.signals import post_save
from django.dispatch import receiver

# Create your models here.
class Drug(models.Model):
    CATEGORY_CHOICES = [
        ('antibiotic', '抗生素'),
        ('antiviral', '抗病毒'),
        ('antipyretic', '解热镇痛'),
        ('cold', '感冒药'),
        ('cardiovascular', '心血管'),
        ('diabetes', '降糖药'),
        ('digestive', '消化系统'),
        ('respiratory', '呼吸系统'),
        ('vitamin', '维生素'),
        ('other', '其他'),
    ]
    
    name = models.CharField(max_length=100, verbose_name="名称", help_text="药品名称")
    specification = models.CharField(
        max_length=50,
        blank=True,
        default='',
        verbose_name="规格",
        help_text="药品规格，如片剂/胶囊/盒装",
    )
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='other', verbose_name="分类", help_text="药品分类")
    stock = models.IntegerField(default=0, verbose_name="库存", help_text="药品库存数量", validators=[MinValueValidator(0)])
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="成本价格", help_text="药品成本价格（元）")
    expiry_date = models.DateField(verbose_name="有效期", help_text="药品有效期", null=True, blank=True)
    min_stock = models.IntegerField(default=10, verbose_name="安全库存下限")
    expiry_warning_days = models.IntegerField(default=30, verbose_name="效期预警提前天数")
    department = models.CharField(max_length=100, blank=True, default='', verbose_name="所属科室", help_text="为空表示全院共用")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    class Meta:
        verbose_name = "药品"
        verbose_name_plural = "药品"
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def is_expiring_soon(self, days=None):
        """检查是否即将过期（默认使用 expiry_warning_days）"""
        if not self.expiry_date:
            return False
        from datetime import date, timedelta
        d = days if days is not None else (self.expiry_warning_days or 30)
        return self.expiry_date <= date.today() + timedelta(days=d)

    def is_low_stock(self, threshold=None):
        """检查是否库存不足（默认与 min_stock 比较）"""
        t = threshold if threshold is not None else (self.min_stock or 0)
        return self.stock <= t


class MedicationRecord(models.Model):
    """用药记录"""
    STATUS_CHOICES = [
        ('ACTIVE', '有效'),
        ('CANCELLED', '已作废'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="用户", related_name="medication_records")
    drug = models.ForeignKey(Drug, on_delete=models.CASCADE, verbose_name="药品", related_name="medication_records")
    prescription_id = models.CharField(max_length=50, verbose_name="处方号", help_text="处方编号，同一处方的记录具有相同的处方号", db_index=True, default='', blank=True)
    quantity = models.IntegerField(verbose_name="领药数量", help_text="领取的药品数量", validators=[MinValueValidator(1)])
    record_time = models.DateTimeField(verbose_name="记录时间")
    notes = models.TextField(blank=True, null=True, verbose_name="备注")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE', verbose_name="状态", db_index=True)
    prescribed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='prescriptions_written',
        verbose_name='开具医师',
        help_text='创建该条用药/处方记录的医师（用于撤销权限）',
    )
    disease_name = models.CharField(max_length=100, blank=True, default='', verbose_name="疾病/诊断标签", db_index=True)
    department = models.CharField(max_length=100, blank=True, default='', verbose_name="科室", db_index=True)
    cancelled_at = models.DateTimeField(null=True, blank=True, verbose_name="作废时间")

    class Meta:
        verbose_name = "用药记录"
        verbose_name_plural = "用药记录"
        ordering = ['-record_time']

    def __str__(self):
        return f"{self.user.username} - {self.drug.name} - {self.quantity}件"


class UserProfile(models.Model):
    """用户扩展信息（角色）"""
    ROLE_CHOICES = [
        ('admin', '管理员'),
        ('doctor', '医生'),
        ('pharmacist', '药剂师'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile', verbose_name="用户")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='doctor', verbose_name="角色")
    avatar = models.URLField(max_length=500, blank=True, default='', verbose_name="头像")
    department = models.CharField(max_length=100, blank=True, default='', verbose_name="科室")

    class Meta:
        verbose_name = "用户角色"
        verbose_name_plural = "用户角色"

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"


class Announcement(models.Model):
    title = models.CharField(max_length=200, verbose_name="标题")
    content = models.TextField(verbose_name="内容")
    is_active = models.BooleanField(default=True, verbose_name="启用")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        verbose_name = "公告"
        verbose_name_plural = "公告"
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class Policy(models.Model):
    title = models.CharField(max_length=200, verbose_name="标题")
    content = models.TextField(verbose_name="内容")
    is_active = models.BooleanField(default=True, verbose_name="启用")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        verbose_name = "政策更新"
        verbose_name_plural = "政策更新"
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class InventoryAdjustment(models.Model):
    drug = models.ForeignKey(Drug, on_delete=models.CASCADE, related_name='inventory_adjustments', verbose_name="药品")
    quantity_change = models.IntegerField(verbose_name="数量变动", help_text="正数为增加，负数为减少")
    reason = models.CharField(max_length=500, verbose_name="原因")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='inventory_adjustments', verbose_name="操作人")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        verbose_name = "库存盘点/损溢"
        verbose_name_plural = "库存盘点/损溢"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.drug.name} {self.quantity_change:+d}"


class OperationLog(models.Model):
    ACTION_CHOICES = [
        ('CREATE_PRESCRIPTION', 'CREATE_PRESCRIPTION'),
        ('CANCEL_PRESCRIPTION', 'CANCEL_PRESCRIPTION'),
        ('STOCK_IN', 'STOCK_IN'),
        ('INVENTORY_ADJUST', 'INVENTORY_ADJUST'),
        ('UPDATE_DRUG', 'UPDATE_DRUG'),
        ('CREATE_USER', 'CREATE_USER'),
        ('UPDATE_USER_ROLE', 'UPDATE_USER_ROLE'),
        ('CREATE_ANNOUNCEMENT', 'CREATE_ANNOUNCEMENT'),
        ('UPDATE_ANNOUNCEMENT', 'UPDATE_ANNOUNCEMENT'),
        ('DELETE_ANNOUNCEMENT', 'DELETE_ANNOUNCEMENT'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='operation_logs')
    action_type = models.CharField(max_length=40, choices=ACTION_CHOICES, db_index=True)
    target_type = models.CharField(max_length=40, blank=True, default='')
    target_id = models.IntegerField(default=0)
    detail = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = '操作审计'
        verbose_name_plural = '操作审计'

    def __str__(self):
        return f'{self.action_type} {self.target_type}:{self.target_id}'


class Alert(models.Model):
    TYPE_CHOICES = [
        ('LOW_STOCK', 'LOW_STOCK'),
        ('EXPIRY', 'EXPIRY'),
        ('DISEASE_TREND', 'DISEASE_TREND'),
        ('ARRIVAL', 'ARRIVAL'),
    ]
    ROLE_CHOICES = [
        ('doctor', 'doctor'),
        ('pharmacist', 'pharmacist'),
        ('admin', 'admin'),
    ]

    type = models.CharField(max_length=30, choices=TYPE_CHOICES, db_index=True)
    level = models.CharField(max_length=20, default='info')
    content = models.TextField()
    target_role = models.CharField(max_length=20, choices=ROLE_CHOICES, db_index=True)
    is_read = models.BooleanField(default=False)
    department = models.CharField(max_length=100, blank=True, default='')
    target_type = models.CharField(max_length=40, blank=True, default='')
    target_id = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = '预警'
        verbose_name_plural = '预警'

    def __str__(self):
        return f'{self.type} {self.target_role}'


# 信号：创建用户时自动创建UserProfile
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)