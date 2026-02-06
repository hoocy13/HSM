from django.contrib.auth.models import User
from rest_framework import authentication
from rest_framework import exceptions


class SimpleTokenAuthentication(authentication.BaseAuthentication):
    """
    与前端 localStorage token 格式一致：simple_token_<user_id>
    请求头：Authorization: Bearer simple_token_<id>
    """

    keyword = b'Bearer'

    def authenticate(self, request):
        auth = authentication.get_authorization_header(request)
        if not auth:
            return None
        parts = auth.split()
        if len(parts) != 2 or parts[0].lower() != self.keyword.lower():
            return None
        token = parts[1].decode('utf-8')
        if not token.startswith('simple_token_'):
            return None
        try:
            user_id = int(token.replace('simple_token_', '', 1))
        except ValueError:
            raise exceptions.AuthenticationFailed('无效的 token')
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            raise exceptions.AuthenticationFailed('用户不存在')
        return (user, None)
