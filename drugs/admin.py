from django.contrib import admin
from .models import (
    Announcement,
    Policy,
    InventoryAdjustment,
    MedicationRecord,
    Drug,
    OperationLog,
    Alert,
)


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active', 'created_at')
    list_filter = ('is_active',)


@admin.register(Policy)
class PolicyAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active', 'created_at')
    list_filter = ('is_active',)


@admin.register(InventoryAdjustment)
class InventoryAdjustmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'drug', 'quantity_change', 'reason', 'created_by', 'created_at')


@admin.register(OperationLog)
class OperationLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'action_type', 'target_type', 'target_id', 'user', 'created_at')
    list_filter = ('action_type',)


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ('id', 'type', 'level', 'target_role', 'department', 'is_read', 'created_at')
    list_filter = ('type', 'target_role', 'is_read')


admin.site.register(Drug)
admin.site.register(MedicationRecord)
