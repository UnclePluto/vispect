from django.db import migrations

class Migration(migrations.Migration):
    dependencies=[('accounts','0001_initial'),('sessions','0001_initial')]
    operations=[migrations.RunSQL([
        'GRANT SELECT,INSERT,UPDATE,DELETE ON accounts_account TO vispect_app,vispect_control',
        'GRANT SELECT,INSERT,UPDATE,DELETE ON tenants_tenant TO vispect_control',
        'GRANT SELECT ON tenants_tenant TO vispect_app',
        'GRANT SELECT,INSERT,UPDATE,DELETE ON django_session TO vispect_control',
    ])]
