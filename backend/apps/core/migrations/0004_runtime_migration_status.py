from django.db import migrations
class Migration(migrations.Migration):
    dependencies=[('core','0003_quota_lock_policy')]
    operations=[migrations.RunSQL('GRANT SELECT ON django_migrations TO vispect_app','REVOKE SELECT ON django_migrations FROM vispect_app')]
