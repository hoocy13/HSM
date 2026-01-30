from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator

# Create your models here.
class Drug(models.Model):
    name = models.CharField(max_length=100, verbose_name="名称", help_text="药品名称")
    stock = models.IntegerField(default=0, verbose_name="库存", help_text="药品库存数量", validators=[MinValueValidator(0)])
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
    quantity = models.IntegerField(verbose_name="领药数量", help_text="领取的药品数量", validators=[MinValueValidator(1)])
    record_time = models.DateTimeField(auto_now_add=True, verbose_name="记录时间")
    notes = models.TextField(blank=True, null=True, verbose_name="备注")
    
    class Meta:
        verbose_name = "用药记录"
        verbose_name_plural = "用药记录"
        ordering = ['-record_time']
    
    def __str__(self):
        return f"{self.user.username} - {self.drug.name} - {self.quantity}件"