from django.core.exceptions import ValidationError
from .errors import ApiError

def ensure_revision(instance,expected_revision):
    if instance.revision != expected_revision:
        raise ApiError('revision_conflict','记录已被其他人修改，请刷新后重试')

def get_object(queryset,object_id,lock=False,*,no_key=False):
    try:obj=(queryset.select_for_update(no_key=no_key) if lock else queryset).filter(id=object_id).first()
    except (ValidationError,ValueError):obj=None
    if obj is None:raise ApiError('object_unavailable','对象不存在或当前不可访问',status=404)
    return obj
