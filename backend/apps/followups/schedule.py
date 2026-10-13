from datetime import date,timedelta
from zoneinfo import ZoneInfo
from django.utils import timezone
from apps.core.errors import ApiError

def local_today(moment=None):return (moment or timezone.now()).astimezone(ZoneInfo('Asia/Shanghai')).date()
def schedule_date(enrolled_on,offset_days):
    if type(enrolled_on)!=date or type(offset_days)!=int or not -36500<=offset_days<=36500:raise ApiError('invalid_date','计划日期参数无效',status=400)
    try:return enrolled_on+timedelta(days=offset_days)
    except OverflowError:raise ApiError('invalid_date','计划日期超出范围',status=400)
