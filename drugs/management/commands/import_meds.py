"""
导入药品数据的管理命令
使用方法: python manage.py import_meds
从 meds.csv 文件导入药品数据，并生成模拟用药记录
"""
import csv
import random
import math
from datetime import date, timedelta, datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import User
from drugs.models import Drug, MedicationRecord, UserProfile, InventoryAdjustment, Alert, OperationLog
from drugs.services.alert_service import maybe_alerts_for_drug, maybe_disease_spike_alert


class Command(BaseCommand):
    help = '从 meds.csv 导入药品数据并生成模拟用药记录'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='meds.csv',
            help='CSV文件路径（默认: meds.csv）'
        )
        parser.add_argument(
            '--skip-drugs',
            action='store_true',
            help='跳过药品导入，只生成用药记录'
        )
        parser.add_argument(
            '--skip-records',
            action='store_true',
            help='跳过用药记录生成，只导入药品'
        )
        parser.add_argument(
            '--start-date',
            type=str,
            default='2025-08-01',
            help='模拟用药记录开始日期（YYYY-MM-DD，默认: 2025-08-01）'
        )
        parser.add_argument(
            '--end-date',
            type=str,
            default='2026-04-10',
            help='模拟用药记录结束日期（YYYY-MM-DD，默认: 2026-04-10）'
        )
        parser.add_argument(
            '--reset-enhancements',
            action='store_true',
            help='生成前清理增强模块数据（MedicationRecord/InventoryAdjustment/Alert/OperationLog），并重置药品库存'
        )

    def handle(self, *args, **options):
        file_path = options['file']
        skip_drugs = options['skip_drugs']
        skip_records = options['skip_records']
        start_date_str = options['start_date']
        end_date_str = options['end_date']
        reset_enhancements = options['reset_enhancements']

        try:
            start_date = timezone.make_aware(datetime.strptime(start_date_str, '%Y-%m-%d'))
            end_date = timezone.make_aware(datetime.strptime(end_date_str, '%Y-%m-%d'))
            # 结束日期包含当天的 23:59:59
            end_date = end_date.replace(hour=23, minute=59, second=59)
        except ValueError:
            self.stdout.write(self.style.ERROR('日期格式错误，请使用 YYYY-MM-DD'))
            return

        if end_date <= start_date:
            self.stdout.write(self.style.ERROR('end-date 必须大于 start-date'))
            return

        # 导入药品数据
        if not skip_drugs:
            self.stdout.write('开始导入药品数据...')
            imported_count = self.import_drugs(file_path)
            self.stdout.write(
                self.style.SUCCESS(f'成功导入 {imported_count} 条药品数据')
            )
        else:
            self.stdout.write('跳过药品导入')
        
        # 从数据库重新获取所有药品（确保有id）
        drugs = list(Drug.objects.all())
        self.stdout.write(f'当前数据库中共有 {len(drugs)} 条药品数据')

        # 生成模拟用药记录
        if not skip_records:
            self.stdout.write('开始生成模拟用药记录...')
            if reset_enhancements:
                self.stdout.write('清理旧的模拟数据（增强模块）...')
                MedicationRecord.objects.all().delete()
                InventoryAdjustment.objects.all().delete()
                Alert.objects.all().delete()
                OperationLog.objects.all().delete()
                self.stdout.write(self.style.SUCCESS('已清空 MedicationRecord / InventoryAdjustment / Alert / OperationLog'))
            
            record_count = self.generate_medication_records(drugs, start_date=start_date, end_date=end_date, reset_stocks=reset_enhancements)
            self.stdout.write(
                self.style.SUCCESS(f'成功生成 {record_count} 条用药记录')
            )
        else:
            self.stdout.write('跳过用药记录生成')

        self.stdout.write(self.style.SUCCESS('导入完成！'))

    def import_drugs(self, file_path):
        """从CSV文件导入药品数据"""
        imported_count = 0
        encodings = ['utf-8-sig', 'utf-8', 'gbk', 'gb2312', 'gb18030']
        
        # 尝试不同的编码
        file_content = None
        used_encoding = None
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    file_content = f.readlines()
                    used_encoding = encoding
                    break
            except (UnicodeDecodeError, FileNotFoundError):
                continue
        
        if file_content is None:
            self.stdout.write(
                self.style.ERROR(f'无法读取文件 {file_path}，请检查文件是否存在和编码格式')
            )
            return 0

        self.stdout.write(f'使用编码: {used_encoding}')

        # 读取药品名称（每行一个）
        drug_names = []
        for line in file_content:
            line = line.strip()
            if line:  # 跳过空行
                # 如果是CSV格式，尝试解析
                try:
                    reader = csv.reader([line])
                    row = next(reader)
                    if row:
                        drug_name = row[0].strip()
                        if drug_name:
                            drug_names.append(drug_name)
                except:
                    # 如果不是CSV格式，直接使用整行作为药品名称
                    drug_names.append(line)

        self.stdout.write(f'读取到 {len(drug_names)} 个药品名称')

        # 批量创建药品
        batch_size = 100
        for i in range(0, len(drug_names), batch_size):
            batch_names = drug_names[i:i + batch_size]
            drug_objects = []
            
            for name in batch_names:
                # 检查是否已存在
                if Drug.objects.filter(name=name).exists():
                    continue
                
                # 随机生成库存（10-500）
                stock = random.randint(10, 500)
                
                # 随机生成成本价格（5-200元）
                cost_price = round(random.uniform(5.0, 200.0), 2)
                
                # 随机生成有效期（30天到2年后）
                days_from_now = random.randint(30, 730)
                expiry_date = date.today() + timedelta(days=days_from_now)
                
                drug = Drug(
                    name=name,
                    stock=stock,
                    cost_price=cost_price,
                    expiry_date=expiry_date
                )
                drug_objects.append(drug)
            
            # 批量创建
            if drug_objects:
                created = Drug.objects.bulk_create(drug_objects, ignore_conflicts=True)
                imported_count += len(created)
                self.stdout.write(f'已导入 {min(i + batch_size, len(drug_names))}/{len(drug_names)} 条药品')

        return imported_count

    def generate_medication_records(self, drugs, start_date, end_date, reset_stocks=False):
        """生成模拟用药记录（优化版：包含高频关联组合和正态分布时间）"""
        if not drugs:
            self.stdout.write(self.style.WARNING('没有药品数据，无法生成用药记录'))
            return 0

        departments = ['内科', '外科', '儿科', '呼吸科', '心内科', '内分泌科']

        def ensure_user(username, role='doctor', department=''):
            user, created = User.objects.get_or_create(
                username=username,
                defaults={'email': f'{username}@example.com'}
            )
            if created:
                user.set_password('123456')
                user.save()
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.role = role
            profile.department = department or ''
            profile.save()
            return user

        # 创建/确保一批用户（病人+医生+药剂师，按科室分配）
        demo_users = [ensure_user(f'demo_user_{i}', role='doctor', department=random.choice(departments)) for i in range(1, 21)]
        doctors = [ensure_user(f'doctor_{dept}', role='doctor', department=dept) for dept in departments]
        pharmacists = [ensure_user(f'pharmacist_{dept}', role='pharmacist', department=dept) for dept in departments]

        users = list(User.objects.all())

        # 可选：重置药品库存与科室（避免重复执行后库存越来越小）
        if reset_stocks:
            self.stdout.write('重置药品库存与部分科室字段...')
            for d in drugs:
                d.stock = random.randint(80, 600)
                # 50% 设为全院共用，50% 归属某科室
                d.department = '' if random.random() < 0.5 else random.choice(departments)
                d.save(update_fields=['stock', 'department'])
                # 生成一条“初始入库”流水，并回写 created_at 到历史时间（用于库存趋势图）
                adj = InventoryAdjustment.objects.create(
                    drug=d,
                    quantity_change=d.stock,
                    reason='初始入库（模拟数据）',
                    created_by=random.choice(pharmacists) if pharmacists else None,
                )
                back_date = start_date + timedelta(days=random.randint(0, max(1, (end_date.date() - start_date.date()).days)))
                InventoryAdjustment.objects.filter(id=adj.id).update(created_at=back_date)

        # 识别高频关联药品组合（通过关键词匹配）
        # 定义3-5组高频关联药品组合
        high_frequency_pairs = []
        
        # 查找包含特定关键词的药品
        def find_drugs_by_keywords(keywords):
            found = []
            for drug in drugs:
                if any(keyword in drug.name for keyword in keywords):
                    found.append(drug)
            return found
        
        # 组合1：感冒灵 + 布洛芬
        cold_medicine = find_drugs_by_keywords(['感冒', '感冒灵', '连花', '双黄连'])
        ibuprofen = find_drugs_by_keywords(['布洛芬', '对乙酰', '退热'])
        if cold_medicine and ibuprofen:
            high_frequency_pairs.append({
                'drugs': [random.choice(cold_medicine), random.choice(ibuprofen)],
                'target_count': random.randint(50, 100),
                'name': '感冒灵+布洛芬'
            })
        
        # 组合2：阿司匹林 + 氯吡格雷
        aspirin = find_drugs_by_keywords(['阿司匹林', '阿斯匹林'])
        clopidogrel = find_drugs_by_keywords(['氯吡格雷', '波立维'])
        if aspirin and clopidogrel:
            high_frequency_pairs.append({
                'drugs': [random.choice(aspirin), random.choice(clopidogrel)],
                'target_count': random.randint(50, 100),
                'name': '阿司匹林+氯吡格雷'
            })
        
        # 组合3：抗生素 + 益生菌
        antibiotic = find_drugs_by_keywords(['霉素', '头孢', '青霉素', '抗生素'])
        probiotic = find_drugs_by_keywords(['益生菌', '双歧', '乳酸菌'])
        if antibiotic and probiotic:
            high_frequency_pairs.append({
                'drugs': [random.choice(antibiotic), random.choice(probiotic)],
                'target_count': random.randint(50, 100),
                'name': '抗生素+益生菌'
            })
        
        # 组合4：降压药 + 利尿剂
        antihypertensive = find_drugs_by_keywords(['降压', '地平', '普利', '沙坦'])
        diuretic = find_drugs_by_keywords(['利尿', '氢氯噻嗪', '呋塞米'])
        if antihypertensive and diuretic:
            high_frequency_pairs.append({
                'drugs': [random.choice(antihypertensive), random.choice(diuretic)],
                'target_count': random.randint(50, 100),
                'name': '降压药+利尿剂'
            })
        
        # 组合5：降糖药 + 胰岛素
        antidiabetic = find_drugs_by_keywords(['降糖', '二甲双胍', '格列'])
        insulin = find_drugs_by_keywords(['胰岛素'])
        if antidiabetic and insulin:
            # 确保是不同的药品
            antidiabetic_filtered = [d for d in antidiabetic if '胰岛素' not in d.name]
            if antidiabetic_filtered and insulin:
                high_frequency_pairs.append({
                    'drugs': [random.choice(antidiabetic_filtered), random.choice(insulin)],
                    'target_count': random.randint(50, 100),
                    'name': '降糖药+胰岛素'
                })

        self.stdout.write(f'识别到 {len(high_frequency_pairs)} 组高频关联药品组合')
        for pair in high_frequency_pairs:
            self.stdout.write(f'  - {pair["name"]}: 目标生成 {pair["target_count"]} 次')

        total_days = (end_date.date() - start_date.date()).days
        if total_days <= 0:
            self.stdout.write(self.style.ERROR('日期范围过短，无法生成数据'))
            return 0

        disease_pool = ['感冒', '流感', '高血压', '糖尿病', '冠心病', '胃炎', '咽炎', '支气管炎']

        def infer_disease(drug_name: str, record_dt: datetime):
            n = drug_name or ''
            if any(k in n for k in ['胰岛素', '二甲双胍', '格列', '降糖']):
                return '糖尿病'
            if any(k in n for k in ['降压', '地平', '普利', '沙坦', '氢氯噻嗪', '呋塞米']):
                return '高血压'
            if any(k in n for k in ['阿司匹林', '氯吡格雷', '波立维']):
                return '冠心病'
            if any(k in n for k in ['感冒', '退热', '止咳', '抗病毒', '连花', '双黄连']):
                # 12-2 月更偏向“流感”
                return '流感' if record_dt.month in [12, 1, 2] and random.random() < 0.6 else '感冒'
            if any(k in n for k in ['头孢', '霉素', '青霉素', '抗生素']):
                return random.choice(['咽炎', '支气管炎', '感冒'])
            return random.choice(disease_pool)

        records = []
        prescription_counter = 1
        batch_size = 500

        # 第一步：生成高频关联组合的处方
        self.stdout.write('生成高频关联组合处方...')
        for pair_info in high_frequency_pairs:
            target_count = pair_info['target_count']
            pair_drugs = pair_info['drugs']
            
            for _ in range(target_count):
                # 使用均匀分布生成日期（start_date ~ end_date）
                days_ago = random.randint(0, total_days - 1)
                record_date = start_date + timedelta(days=days_ago)
                
                # 生成处方号
                prescription_id = f'RX{prescription_counter:08d}'
                prescription_counter += 1
                
                # 随机选择患者与开方医生（决定科室隔离字段）
                user = random.choice(demo_users) if demo_users else random.choice(users)
                doctor = random.choice(doctors) if doctors else None
                dept = (doctor.profile.department if doctor and hasattr(doctor, 'profile') else '') or ''
                disease_name = infer_disease(pair_drugs[0].name, record_date)
                
                # 为同一处方生成多条记录（同一处方下的所有药品）
                for drug in pair_drugs:
                    quantity = random.randint(1, 10)
                    hour = random.randint(8, 18)
                    minute = random.randint(0, 59)
                    second = random.randint(0, 59)
                    # 使用 datetime.combine 确保时区正确
                    from datetime import time as dt_time
                    # record_date 已经是 datetime 对象，直接使用
                    record_time = record_date.replace(hour=hour, minute=minute, second=second)
                    
                    record = MedicationRecord(
                        user_id=user.id,
                        drug_id=drug.id,
                        prescription_id=prescription_id,
                        quantity=quantity,
                        record_time=record_time,
                        notes=None,
                        status='ACTIVE',
                        prescribed_by=doctor,
                        disease_name=disease_name,
                        department=dept,
                    )
                    records.append(record)
                    
                    if len(records) >= batch_size:
                        MedicationRecord.objects.bulk_create(records, ignore_conflicts=True)
                        records = []

        # 第二步：生成普通处方（随机组合，count 1-5）
        self.stdout.write('生成普通处方...')
        target_count = 10000
        high_freq_count = sum(pair['target_count'] * len(pair['drugs']) for pair in high_frequency_pairs)
        remaining_count = max(0, target_count - high_freq_count)
        
        # 计算需要生成的处方数量（每个处方1-3种药品）
        avg_drugs_per_prescription = 2
        num_prescriptions = remaining_count // avg_drugs_per_prescription
        
        for i in range(num_prescriptions):
            # 使用均匀分布生成日期（start_date ~ end_date）
            days_ago = random.randint(0, total_days - 1)
            record_date = start_date + timedelta(days=days_ago)
            # 确保 record_date 是 datetime 对象
            if not isinstance(record_date, datetime):
                record_date = datetime.combine(record_date, datetime.min.time())
                record_date = timezone.make_aware(record_date)
            
            # 模拟季节性：冬季（12-2月）感冒类药品消耗增加
            month = record_date.month
            is_winter = month in [12, 1, 2]
            
            # 生成处方号
            prescription_id = f'RX{prescription_counter:08d}'
            prescription_counter += 1
            
            # 随机选择患者与开方医生
            user = random.choice(demo_users) if demo_users else random.choice(users)
            doctor = random.choice(doctors) if doctors else None
            dept = (doctor.profile.department if doctor and hasattr(doctor, 'profile') else '') or ''
            
            # 每个处方随机包含1-3种药品
            num_drugs_in_prescription = random.randint(1, 3)
            
            # 如果是冬季，增加感冒类药品的概率
            if is_winter and random.random() < 0.3:
                # 30%概率选择感冒类药品
                cold_drugs = [d for d in drugs if any(keyword in d.name for keyword in ['感冒', '退热', '止咳', '抗病毒'])]
                if cold_drugs:
                    selected_drugs = random.sample(cold_drugs, min(num_drugs_in_prescription, len(cold_drugs)))
                else:
                    selected_drugs = random.sample(drugs, min(num_drugs_in_prescription, len(drugs)))
            else:
                selected_drugs = random.sample(drugs, min(num_drugs_in_prescription, len(drugs)))
            
            disease_name = infer_disease(selected_drugs[0].name if selected_drugs else '', record_date)
            for drug in selected_drugs:
                quantity = random.randint(1, 10)
                hour = random.randint(8, 18)
                minute = random.randint(0, 59)
                second = random.randint(0, 59)
                # 使用 datetime.combine 确保时区正确
                from datetime import time as dt_time
                record_time = timezone.make_aware(
                    datetime.combine(record_date.date(), dt_time(hour, minute, second))
                )
                
                # 生成备注（30%概率）
                notes = None
                if random.random() < 0.3:
                    note_templates = [
                        '常规用药',
                        '按医嘱服用',
                        '饭后服用',
                        '每日三次',
                        '症状缓解后停药'
                    ]
                    notes = random.choice(note_templates)
                
                record = MedicationRecord(
                    user_id=user.id,
                    drug_id=drug.id,
                    prescription_id=prescription_id,
                    quantity=quantity,
                    record_time=record_time,
                    notes=notes,
                    status='ACTIVE',
                    prescribed_by=doctor,
                    disease_name=disease_name,
                    department=dept,
                )
                records.append(record)
            
            # 批量保存
            if len(records) >= batch_size:
                MedicationRecord.objects.bulk_create(records, ignore_conflicts=True)
                self.stdout.write(f'已生成 {i + 1}/{num_prescriptions} 个普通处方')
                records = []

        # 保存剩余的记录
        if records:
            MedicationRecord.objects.bulk_create(records, ignore_conflicts=True)

        # 更新药品库存（扣除已使用的数量）
        self.stdout.write('更新药品库存...')
        self.update_drug_stocks()

        # 生成预警（用于首页/仪表盘展示）
        self.stdout.write('生成预警（Alert）...')
        for d in Drug.objects.all():
            maybe_alerts_for_drug(d, d.department or '')
        # 疾病趋势预警（按科室+疾病名做一次检查）
        sampled = MedicationRecord.objects.filter(status='ACTIVE').values_list('disease_name', 'department').distinct()[:50]
        for dn, dept in sampled:
            maybe_disease_spike_alert(dn or '', dept or '')

        total_records = MedicationRecord.objects.count()
        return total_records

    def update_drug_stocks(self):
        """根据用药记录更新药品库存"""
        # 按药品统计总消耗量
        from django.db.models import Sum
        consumption = MedicationRecord.objects.values('drug').annotate(
            total_consumption=Sum('quantity')
        )
        
        updated_count = 0
        # 更新每个药品的库存
        for item in consumption:
            drug_id = item['drug']
            total_consumption = item['total_consumption']
            
            try:
                drug = Drug.objects.get(id=drug_id)
                # 确保库存不为负数
                new_stock = max(0, drug.stock - total_consumption)
                drug.stock = new_stock
                drug.save()
                updated_count += 1
            except Drug.DoesNotExist:
                continue
        
        self.stdout.write(f'已更新 {updated_count} 个药品的库存')
