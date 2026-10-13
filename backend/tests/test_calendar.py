from datetime import timedelta
from apps.core.context import tenant_transaction
from apps.followups.schedule import local_today

def test_calendar_uses_window_end_and_current_permissions(world):
    e,v,b=world.entry('a');a=world.actor('a','doctor');today=local_today()
    v.window_end=today-timedelta(days=1);world.owner_save(v)
    with tenant_transaction(a.tenant_id):future=e.visits.exclude(id=v.id).first()
    response=world.login('a','doctor').get('/api/calendar/');assert response.status_code==200
    records={r['id']:r for r in response.json()['results']}
    assert records[str(v.id)]['color']=='red' and records[str(future.id)]['color']=='yellow'
    future.status='completed';world.owner_save(future)
    response=world.login('a','doctor').get('/api/calendar/');records={r['id']:r for r in response.json()['results']}
    assert records[str(future.id)]['color']=='blue'
    assert world.login(None,'platform_admin').get('/api/calendar/').status_code==403
    assert world.login('b','doctor').get('/api/calendar/').json()['count']==0

def test_outside_window_does_not_block_entry(world):
    from apps.followups.answers import submit_answer
    e,v,b=world.entry('a');v.window_end=local_today()-timedelta(days=1);world.owner_save(v)
    assert submit_answer(world.actor('a','doctor'),v.id,b.id,{'q1':'补录'},'late').status=='submitted'
