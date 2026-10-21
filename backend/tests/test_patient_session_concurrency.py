from concurrent.futures import ThreadPoolExecutor
from threading import Event
from django.db import connections
from rest_framework.test import APIRequestFactory
from django.conf import settings
from tests.patient_portal_helpers import portal_world,login_patient,patient_post


def test_password_change_waits_for_authorized_request_and_revokes_old_cookie(world):
    from apps.patient_portal.sessions import patient_transaction
    portal=portal_world(world);client,response=login_patient(portal)
    old_cookie=client.cookies[settings.PATIENT_SESSION_COOKIE_NAME].value
    token=response.json()['session_token'];held=Event();release=Event();started=Event();finished=Event()
    def read():
        connections.close_all()
        request=APIRequestFactory().get('/api/patient/test/',HTTP_X_PATIENT_SESSION_TOKEN=token)
        request.COOKIES[settings.PATIENT_SESSION_COOKIE_NAME]=old_cookie
        try:
            with patient_transaction(request,require_changed_password=False):
                held.set();assert release.wait(10)
        finally:connections.close_all()
    def change():
        connections.close_all();started.set()
        try:
            result=patient_post(client,'/api/patient/auth/change-password/',{'old_password':'888888','new_password':'Patient-Changed-Password-2026!'})
            finished.set();return result.status_code
        finally:connections.close_all()
    with ThreadPoolExecutor(max_workers=2) as pool:
        reader=pool.submit(read);assert held.wait(10)
        writer=pool.submit(change);assert started.wait(10)
        assert not finished.wait(.15)
        release.set();reader.result(timeout=10);assert writer.result(timeout=10)==200
    from apps.patient_portal.scope_store import resolve_session_scope
    assert resolve_session_scope(old_cookie) is None


def test_expired_patient_session_is_rejected(world):
    from datetime import timedelta
    from django.utils import timezone
    from apps.core.context import tenant_transaction
    from apps.patient_portal.models import PatientSession
    portal=portal_world(world);client,_=login_patient(portal)
    with tenant_transaction(portal.actor.tenant_id):PatientSession.objects.update(expires_at=timezone.now()-timedelta(seconds=1))
    assert client.get('/api/patient/auth/me/').status_code==401
