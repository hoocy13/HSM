"""
创建默认管理员账户的管理命令
使用方法: python manage.py create_admin
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from drugs.models import UserProfile


class Command(BaseCommand):
    help = '创建默认管理员账户 (username: admin, password: admin)'

    def handle(self, *args, **options):
        username = 'admin'
        password = 'admin'
        email = 'admin@example.com'

        # 检查用户是否已存在
        if User.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.WARNING(f'用户 "{username}" 已存在，跳过创建')
            )
            # 如果存在，更新密码和角色
            user = User.objects.get(username=username)
            user.set_password(password)
            user.is_staff = True
            user.is_superuser = True
            user.save()
            
            # 更新或创建用户角色
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.role = 'admin'
            profile.save()
            
            self.stdout.write(
                self.style.SUCCESS(f'已更新用户 "{username}" 的密码为 "{password}"，角色为管理员')
            )
        else:
            # 创建新用户
            user = User.objects.create_superuser(
                username=username,
                email=email,
                password=password
            )
            
            # 创建用户角色
            UserProfile.objects.get_or_create(user=user, defaults={'role': 'admin'})
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'成功创建管理员账户:\n'
                    f'  用户名: {username}\n'
                    f'  密码: {password}\n'
                    f'  邮箱: {email}\n'
                    f'  角色: 管理员'
                )
            )
