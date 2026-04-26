from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('drugs', '0012_sync_drug_specification_field'),
    ]

    operations = [
        migrations.AddField(
            model_name='medicationrecord',
            name='dispense_status',
            field=models.CharField(
                choices=[('pending', '待审批发药'), ('dispensed', '已发药')],
                db_index=True,
                default='dispensed',
                help_text='医师开具后为待审批；药剂师同意发药后扣减库存并置为已发药',
                max_length=20,
                verbose_name='发药状态',
            ),
        ),
        migrations.AddField(
            model_name='medicationrecord',
            name='dispensed_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='发药时间'),
        ),
        migrations.AddField(
            model_name='medicationrecord',
            name='dispensed_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='dispensed_medication_records',
                to=settings.AUTH_USER_MODEL,
                verbose_name='发药人',
            ),
        ),
        migrations.AlterModelOptions(
            name='medicationrecord',
            options={'ordering': ['-record_time', '-id'], 'verbose_name': '用药记录', 'verbose_name_plural': '用药记录'},
        ),
    ]
