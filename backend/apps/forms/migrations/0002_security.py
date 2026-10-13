from django.db import migrations
from apps.core.rls import apply_tenant_rls
class Migration(migrations.Migration):
    dependencies=[('forms','0001_initial')]
    operations=[migrations.RunSQL(apply_tenant_rls('forms_form')+apply_tenant_rls('forms_formversion')+[
        'ALTER TABLE forms_form ADD CONSTRAINT form_owner_tenant_fk FOREIGN KEY (tenant_id,owner_id) REFERENCES accounts_account(tenant_id,id)',
        'ALTER TABLE forms_formversion ADD CONSTRAINT version_form_tenant_fk FOREIGN KEY (tenant_id,form_id) REFERENCES forms_form(tenant_id,id)',
        'ALTER TABLE forms_formversion ADD CONSTRAINT version_publisher_tenant_fk FOREIGN KEY (tenant_id,published_by_id) REFERENCES accounts_account(tenant_id,id)',
        'REVOKE UPDATE,DELETE ON forms_formversion FROM vispect_app',
        'REVOKE DELETE ON forms_form FROM vispect_app',
        """CREATE FUNCTION vispect_immutable_form_version() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'published form versions are immutable' USING ERRCODE='23514'; END; $$""",
        'CREATE TRIGGER immutable_form_version BEFORE UPDATE OR DELETE ON forms_formversion FOR EACH ROW EXECUTE FUNCTION vispect_immutable_form_version()',
    ])]
