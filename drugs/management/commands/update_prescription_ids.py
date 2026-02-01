"""
为现有的用药记录生成处方号
使用方法: python manage.py update_prescription_ids
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from drugs.models import MedicationRecord
from collections import defaultdict


class Command(BaseCommand):
    help = '为现有的用药记录生成处方号'

    def handle(self, *args, **options):
        self.stdout.write('开始为现有用药记录生成处方号...')
        
        # 获取所有没有prescription_id的记录
        records_without_prescription = MedicationRecord.objects.filter(
            prescription_id=''
        ).order_by('record_time', 'user_id')
        
        total_count = records_without_prescription.count()
        self.stdout.write(f'找到 {total_count} 条没有处方号的记录')
        
        if total_count == 0:
            self.stdout.write(self.style.SUCCESS('所有记录都已包含处方号'))
            return
        
        # 按用户和时间分组，将相近时间的记录归为同一处方
        # 策略：同一用户在同一天内的记录，如果时间间隔小于30分钟，归为同一处方
        # 每个处方包含1-3个药品（随机）
        import random
        
        prescription_counter = 1
        updated_count = 0
        
        # 按用户分组
        user_records = defaultdict(list)
        for record in records_without_prescription:
            user_records[record.user_id].append(record)
        
        for user_id, records in user_records.items():
            # 按时间排序
            records.sort(key=lambda r: r.record_time)
            
            i = 0
            while i < len(records):
                # 每个处方包含1-3个药品（随机）
                num_drugs_in_prescription = random.randint(1, 3)
                prescription_id = f'RX{prescription_counter:08d}'
                prescription_counter += 1
                
                # 为当前处方分配药品
                for j in range(num_drugs_in_prescription):
                    if i < len(records):
                        record = records[i]
                        record.prescription_id = prescription_id
                        record.save(update_fields=['prescription_id'])
                        updated_count += 1
                        i += 1
                
                if updated_count % 1000 == 0:
                    self.stdout.write(f'已更新 {updated_count}/{total_count} 条记录...')
        
        self.stdout.write(
            self.style.SUCCESS(f'成功为 {updated_count} 条记录生成了处方号，共生成 {prescription_counter - 1} 个处方')
        )
