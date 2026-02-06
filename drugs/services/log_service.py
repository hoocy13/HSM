"""操作审计日志：在同一 transaction 内与业务一起写入。"""
from ..models import OperationLog


def log_operation(*, user, action_type, target_type, target_id, detail=''):
    OperationLog.objects.create(
        user=user if user and getattr(user, 'is_authenticated', False) else None,
        action_type=action_type,
        target_type=target_type,
        target_id=int(target_id) if target_id is not None else 0,
        detail=(detail or '')[:2000],
    )
