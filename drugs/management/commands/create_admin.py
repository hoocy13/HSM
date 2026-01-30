"""
创建默认管理员账户的管理命令
使用方法: python manage.py create_admin
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


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
            # 如果存在，更新密码
            user = User.objects.get(username=username)
            user.set_password(password)
            user.is_staff = True
            user.is_superuser = True
            user.save()
            self.stdout.write(
                self.style.SUCCESS(f'已更新用户 "{username}" 的密码为 "{password}"')
            )
        else:
            # 创建新用户
            User.objects.create_superuser(
                username=username,
                email=email,
                password=password
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f'成功创建管理员账户:\n'
                    f'  用户名: {username}\n'
                    f'  密码: {password}\n'
                    f'  邮箱: {email}'
                )
            )
