from django.db import migrations
from apps.core.rls import apply_tenant_rls

TABLES=['patientloginidentity','patientaccess','patientformentry','patientsession','patientsubmissionreceipt','patientactivity']
SQL=sum([apply_tenant_rls('patient_portal_'+name) for name in TABLES],[])
for table,column,target in [
    ('patientaccess','patient','patients_patient'),('patientaccess','identity','patient_portal_patientloginidentity'),
    ('patientformentry','binding','studies_formbinding'),('patientformentry','created_by','accounts_account'),('patientformentry','disabled_by','accounts_account'),
    ('patientsession','identity','patient_portal_patientloginidentity'),('patientsubmissionreceipt','identity','patient_portal_patientloginidentity'),
    ('patientsubmissionreceipt','answer','followups_answer'),('patientactivity','identity','patient_portal_patientloginidentity')]:
    SQL.append(f'ALTER TABLE patient_portal_{table} ADD CONSTRAINT portal_{table}_{column}_tenant_fk FOREIGN KEY (tenant_id,{column}_id) REFERENCES {target}(tenant_id,id)')
SQL += [
    'REVOKE DELETE ON patient_portal_patientloginidentity,patient_portal_patientaccess,patient_portal_patientformentry,patient_portal_patientsession FROM vispect_app',
    'REVOKE UPDATE,DELETE ON patient_portal_patientactivity,patient_portal_patientsubmissionreceipt FROM vispect_app',
    'CREATE TRIGGER immutable_patient_activity BEFORE UPDATE OR DELETE ON patient_portal_patientactivity FOR EACH ROW EXECUTE FUNCTION vispect_immutable_answer_history()',
    'CREATE TRIGGER immutable_patient_receipt BEFORE UPDATE OR DELETE ON patient_portal_patientsubmissionreceipt FOR EACH ROW EXECUTE FUNCTION vispect_immutable_answer_history()',
    "CREATE POLICY portal_entry_lookup ON patient_portal_patientformentry FOR SELECT TO vispect_owner USING (token_digest=NULLIF(current_setting('vispect.portal_entry_digest',true),''))",
    "CREATE POLICY portal_session_lookup ON patient_portal_patientsession TO vispect_owner USING (credential_digest=NULLIF(current_setting('vispect.portal_session_digest',true),'')) WITH CHECK (credential_digest=NULLIF(current_setting('vispect.portal_session_digest',true),''))",
    r'''CREATE FUNCTION vispect_patient_entry_scope(p_digest text) RETURNS TABLE(tenant_id uuid,entry_id uuid)
    LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
    DECLARE old_scope text;
    BEGIN
      old_scope:=current_setting('vispect.portal_entry_digest',true);
      PERFORM set_config('vispect.portal_entry_digest',p_digest,true);
      RETURN QUERY SELECT e.tenant_id,e.id FROM public.patient_portal_patientformentry e WHERE e.token_digest=p_digest AND e.enabled AND e.deleted_at IS NULL;
      PERFORM set_config('vispect.portal_entry_digest',COALESCE(old_scope,''),true);
    EXCEPTION WHEN OTHERS THEN
      PERFORM set_config('vispect.portal_entry_digest',COALESCE(old_scope,''),true); RAISE;
    END $$''',
    r'''CREATE FUNCTION vispect_patient_session_scope(p_digest text) RETURNS TABLE(tenant_id uuid,session_id uuid,identity_id uuid)
    LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
    DECLARE old_scope text;
    BEGIN
      old_scope:=current_setting('vispect.portal_session_digest',true);
      PERFORM set_config('vispect.portal_session_digest',p_digest,true);
      RETURN QUERY SELECT s.tenant_id,s.id,s.identity_id FROM public.patient_portal_patientsession s WHERE s.credential_digest=p_digest AND NOT s.revoked AND s.expires_at>now();
      PERFORM set_config('vispect.portal_session_digest',COALESCE(old_scope,''),true);
    EXCEPTION WHEN OTHERS THEN
      PERFORM set_config('vispect.portal_session_digest',COALESCE(old_scope,''),true); RAISE;
    END $$''',
    r'''CREATE FUNCTION vispect_revoke_patient_session(p_digest text) RETURNS boolean
    LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
    DECLARE old_scope text; changed boolean;
    BEGIN
      old_scope:=current_setting('vispect.portal_session_digest',true);
      PERFORM set_config('vispect.portal_session_digest',p_digest,true);
      UPDATE public.patient_portal_patientsession SET revoked=true WHERE credential_digest=p_digest AND NOT revoked;
      changed:=FOUND;
      PERFORM set_config('vispect.portal_session_digest',COALESCE(old_scope,''),true); RETURN changed;
    EXCEPTION WHEN OTHERS THEN
      PERFORM set_config('vispect.portal_session_digest',COALESCE(old_scope,''),true); RAISE;
    END $$''',
]
for fn in ['vispect_patient_entry_scope','vispect_patient_session_scope','vispect_revoke_patient_session']:
    SQL += [f'REVOKE ALL ON FUNCTION {fn}(text) FROM PUBLIC',f'GRANT EXECUTE ON FUNCTION {fn}(text) TO vispect_app']

class Migration(migrations.Migration):
    dependencies=[('patient_portal','0001_initial'),('followups','0004_answer_security')]
    operations=[migrations.RunSQL(SQL)]
