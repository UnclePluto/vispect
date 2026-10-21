import copy
import time
import uuid
import pytest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier,Event
from django.db import connections,connection
from rest_framework.test import APIClient
from apps.core.context import tenant_transaction
from apps.followups.models import Answer
from apps.tenants.models import TenantQuota
from tests.patient_portal_helpers import portal_world,ready_patient
from tests.test_patient_answers import write


def clone_client(client):
    clone=APIClient(enforce_csrf_checks=True);clone.cookies=copy.deepcopy(client.cookies);clone.defaults=dict(client.defaults)
    return clone


def test_same_key_concurrent_submit_has_one_answer(world):
    portal=portal_world(world);client=ready_patient(portal);gate=Barrier(2);key=uuid.uuid4().hex
    def run(_):
        connections.close_all()
        try:
            local=clone_client(client);gate.wait(timeout=10)
            response=write(local,portal,{'q1':'一次答案'},key=key)
            assert response.status_code==200,response.content
            return response.json()['id']
        finally:connections.close_all()
    with ThreadPoolExecutor(max_workers=2) as pool:ids=list(pool.map(run,range(2)))
    assert ids[0]==ids[1]
    with tenant_transaction(portal.actor.tenant_id):assert Answer.objects.filter(visit_id=portal.visit.id).count()==1


@pytest.mark.parametrize('operation',['complete','stop','pause','revoke'])
def test_waiting_submit_rechecks_clinical_state(world,operation):
    portal=portal_world(world,optional=operation=='complete');client=ready_patient(portal)
    started=Event()
    def submit():
        connections.close_all()
        try:
            started.set()
            return write(clone_client(client),portal,{'q1':'迟到答案'})
        finally:connections.close_all()
    with ThreadPoolExecutor(max_workers=1) as pool:
        with tenant_transaction(portal.actor.tenant_id):
            TenantQuota.objects.select_for_update().get(tenant_id=portal.actor.tenant_id)
            future=pool.submit(submit);assert started.wait(10)
            deadline=time.monotonic()+10
            while True:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT EXISTS(SELECT 1 FROM pg_locks WHERE NOT granted)")
                    if cursor.fetchone()[0]:break
                assert time.monotonic()<deadline,'患者写入没有到达数据库锁等待'
                Event().wait(.01)
            if operation=='complete':
                from apps.followups.transitions import complete_visit
                complete_visit(portal.actor,portal.visit.id,uuid.uuid4().hex)
            elif operation=='stop':
                from apps.followups.transitions import stop_followup
                stop_followup(portal.actor,portal.enrollment.id,'withdrawal','患者退出',uuid.uuid4().hex)
            elif operation=='pause':
                from apps.forms.services import set_form_paused
                with tenant_transaction(portal.actor.tenant_id):form=portal.binding.form_version.form
                set_form_paused(world.actor('a','tenant_admin'),form.id,True,form.revision)
            else:
                from apps.patient_portal.entries import change_entry
                change_entry(portal.actor,portal.entry.id,'disable',portal.entry.revision)
        response=future.result(timeout=15)
    assert response.status_code==(404 if operation=='revoke' else 409),response.content
    with tenant_transaction(portal.actor.tenant_id):assert not Answer.objects.filter(visit_id=portal.visit.id).exists()
