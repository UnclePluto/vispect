from datetime import date
from concurrent.futures import ThreadPoolExecutor
import pytest
from django.db import connections
from apps.core.context import tenant_transaction
from apps.core.errors import ApiError

def test_confirmation_is_idempotent(world):
    from apps.followups.enrollments import add_subject,confirm_enrollment
    from apps.followups.models import VisitInstance
    from apps.tenants.models import TenantQuota
    s=world.study('a');p=world.patient('a');a=world.actor('a','doctor')
    e=add_subject(a,s.id,p.id,a.doctor_id,'000001','subject')
    assert add_subject(a,s.id,p.id,a.doctor_id,'000001','subject').id==e.id
    first=confirm_enrollment(a,e.id,'000001',e.added_on,'confirm')
    second=confirm_enrollment(a,e.id,'000001',e.added_on,'confirm')
    assert first.id==second.id and second.enrollment_code=='000001'
    with tenant_transaction(a.tenant_id):assert VisitInstance.objects.filter(enrollment=e).count()==2
    other=world.study('a');add_subject(a,other.id,p.id,a.doctor_id,'same-patient','other-study')
    assert TenantQuota.objects.using('migration').get(tenant_id=a.tenant_id).patients_used==1
    with pytest.raises(ApiError):add_subject(a,s.id,p.id,a.doctor_id,'second','duplicate')

def test_concurrent_confirmations_generate_visits_once(world):
    from apps.followups.enrollments import add_subject,confirm_enrollment
    from apps.followups.models import VisitInstance
    s=world.study('a');p=world.patient('a');a=world.actor('a','doctor');e=add_subject(a,s.id,p.id,a.doctor_id,'obs','add')
    def confirm(key):
        try:return confirm_enrollment(a,e.id,'000001',e.added_on,key).id
        finally:connections.close_all()
    with ThreadPoolExecutor(max_workers=2) as pool:assert list(pool.map(confirm,['same-key','same-key']))==[e.id,e.id]
    with tenant_transaction(a.tenant_id):assert VisitInstance.objects.filter(enrollment=e).count()==2

def test_screening_and_protocol_freeze(world):
    from apps.followups.enrollments import add_subject,confirm_enrollment
    from apps.studies.services import save_protocol
    from apps.followups.models import VisitInstance
    s=world.study('a',screening=True);p=world.patient('a');a=world.actor('a','doctor');e=add_subject(a,s.id,p.id,a.doctor_id,'obs','add')
    assert e.state=='screening'
    with pytest.raises(ApiError):confirm_enrollment(a,e.id,'000001',e.added_on,'confirm')
    with pytest.raises(ApiError) as exc:save_protocol(a,s.id,[],s.revision+1)
    assert exc.value.code=='protocol_frozen'
    with world.owner_context(a.tenant_id):
        visit=VisitInstance.objects.using('migration').get(id=e.current_visit_id);visit.status='completed';visit.save(using='migration')
    e=confirm_enrollment(a,e.id,'000001',e.added_on,'confirm')
    assert e.state=='following'

def test_membership_does_not_open_other_patients(world):
    from apps.followups.enrollments import add_subject
    from apps.followups.selectors import visible_enrollments
    from apps.studies.services import set_study_members
    from apps.core.types import Actor
    a=world.actor('a','doctor');s=world.study('a');p=world.patient('a');e=add_subject(a,s.id,p.id,a.doctor_id,'obs','add');other=world.doctor('a')
    with tenant_transaction(a.tenant_id):s.refresh_from_db()
    set_study_members(a,s.id,[other.id],s.revision)
    actor=Actor(other.account_id,a.tenant_id,'doctor',other.id)
    with tenant_transaction(a.tenant_id):assert not visible_enrollments(actor).exists()
    assert world.login('b','tenant_admin').get(f'/api/enrollments/{e.id}/').status_code==404

def test_transfer_required_before_relationship_removal(world):
    from apps.followups.enrollments import add_subject,transfer_followup
    from apps.patients.services import assign_doctors,delete_patient
    from apps.studies.services import set_study_members
    a=world.actor('a','doctor');admin=world.actor('a','tenant_admin');s=world.study('a');p=world.patient('a');e=add_subject(a,s.id,p.id,a.doctor_id,'obs','add');other=world.doctor('a')
    with pytest.raises(ApiError):assign_doctors(admin,p.id,[other.id],p.revision)
    with pytest.raises(ApiError):delete_patient(admin,p.id,p.revision)
    p=assign_doctors(admin,p.id,[a.doctor_id,other.id],p.revision)
    with tenant_transaction(a.tenant_id):s.refresh_from_db()
    s=set_study_members(admin,s.id,[other.id],s.revision)
    e=transfer_followup(admin,e.id,other.id,e.revision)
    assign_doctors(admin,p.id,[other.id],p.revision)
    assert e.doctor_id==other.id

def test_protocol_is_frozen_in_database(world):
    import psycopg
    from apps.followups.enrollments import add_subject
    a=world.actor('a','doctor');s=world.study('a');p=world.patient('a');add_subject(a,s.id,p.id,a.doctor_id,'obs','add')
    with psycopg.connect(world.app_dsn) as conn:
        conn.execute("SELECT set_config('vispect.tenant_id',%s,true)",[str(a.tenant_id)])
        with pytest.raises(psycopg.errors.CheckViolation):conn.execute('UPDATE studies_visitdefinition SET offset_days=40 WHERE study_id=%s',[s.id])
    with psycopg.connect(world.app_dsn) as conn:
        conn.execute("SELECT set_config('vispect.tenant_id',%s,true)",[str(a.tenant_id)])
        with pytest.raises(psycopg.errors.CheckViolation):conn.execute('UPDATE studies_study SET protocol_frozen=false WHERE id=%s',[s.id])

def test_enrollment_number_and_stage_study_constraint(world):
    import psycopg
    from apps.followups.enrollments import add_subject,confirm_enrollment
    a=world.actor('a','doctor');s=world.study('a');p=world.patient('a');e=add_subject(a,s.id,p.id,a.doctor_id,'obs','add');e=confirm_enrollment(a,e.id,'000001',e.added_on,'confirm')
    other=world.patient('a');e2=add_subject(a,s.id,other.id,a.doctor_id,'obs2','add2')
    with pytest.raises(ApiError) as exc:confirm_enrollment(a,e2.id,'000001',e2.added_on,'confirm2')
    assert exc.value.code=='duplicate_code'
    foreign_study=world.study('a')
    with tenant_transaction(a.tenant_id):foreign_stage=foreign_study.stages.first()
    with psycopg.connect(world.app_dsn) as conn:
        conn.execute("SELECT set_config('vispect.tenant_id',%s,true)",[str(a.tenant_id)])
        with pytest.raises(psycopg.errors.ForeignKeyViolation):conn.execute('UPDATE followups_visitinstance SET stage_id=%s WHERE id=%s',[foreign_stage.id,e.current_visit_id])

def test_replay_rechecks_current_patient_access(world):
    from apps.followups.enrollments import add_subject,transfer_followup
    from apps.patients.services import assign_doctors
    from apps.studies.services import set_study_members
    a=world.actor('a','doctor');admin=world.actor('a','tenant_admin');s=world.study('a');p=world.patient('a');e=add_subject(a,s.id,p.id,a.doctor_id,'obs','add');other=world.doctor('a')
    with tenant_transaction(a.tenant_id):s.refresh_from_db()
    set_study_members(admin,s.id,[other.id],s.revision);p=assign_doctors(admin,p.id,[a.doctor_id,other.id],p.revision)
    transfer_followup(admin,e.id,other.id,e.revision);assign_doctors(admin,p.id,[other.id],p.revision)
    with pytest.raises(ApiError) as exc:add_subject(a,s.id,p.id,a.doctor_id,'obs','add')
    assert exc.value.status==404
