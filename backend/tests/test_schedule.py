from datetime import date,datetime,timezone
import pytest
from apps.followups.schedule import schedule_date,local_today
@pytest.mark.parametrize('start,offset,expected',[(date(2024,2,28),1,date(2024,2,29)),(date(2026,1,31),1,date(2026,2,1)),(date(2026,12,31),1,date(2027,1,1))])
def test_schedule_uses_calendar_days(start,offset,expected):assert schedule_date(start,offset)==expected
def test_local_today_shanghai_midnight():
    assert local_today(datetime(2026,10,12,15,59,tzinfo=timezone.utc))==date(2026,10,12)
    assert local_today(datetime(2026,10,12,16,0,tzinfo=timezone.utc))==date(2026,10,13)
