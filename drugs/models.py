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
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='other', verbose_name="分类", help_text="药品分类")
    stock = models.IntegerField(default=0, verbose_name="库存", help_text="药品库存数量", validators=[MinValueValidator(0)])
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="成本价格", help_text="药品成本价格（元）")
    expiry_date = models.DateField(verbose_name="有效期", help_text="药品有效期", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    class Meta:
        verbose_name = "药品"
        verbose_name_plural = "药品"
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def is_expiring_soon(self, days=30):
        """检查是否即将过期（默认30天内）"""
        if not self.expiry_date:
            return False
        from datetime import date, timedelta
        return self.expiry_date <= date.today() + timedelta(days=days)
    
    def is_low_stock(self, threshold=50):
        """检查是否库存不足（默认低于50件）"""
        return self.stock < threshold


class MedicationRecord(models.Model):
    """用药记录"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="用户", related_name="medication_records")
    drug = models.ForeignKey(Drug, on_delete=models.CASCADE, verbose_name="药品", related_name="medication_records")
    prescription_id = models.CharField(max_length=50, verbose_name="处方号", help_text="处方编号，同一处方的记录具有相同的处方号", db_index=True, default='', blank=True)
    quantity = models.IntegerField(verbose_name="领药数量", help_text="领取的药品数量", validators=[MinValueValidator(1)])
    record_time = models.DateTimeField(verbose_name="记录时间")
    notes = models.TextField(blank=True, null=True, verbose_name="备注")
    
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
        ('patient', '患者'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile', verbose_name="用户")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='patient', verbose_name="角色")
    
    class Meta:
        verbose_name = "用户角色"
        verbose_name_plural = "用户角色"
    
    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"


# 信号：创建用户时自动创建UserProfile
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)