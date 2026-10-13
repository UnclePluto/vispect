from django.db import models
from apps.core.models import TenantRecord,tenant_identity_constraint
class Form(TenantRecord):
    owner=models.ForeignKey('accounts.Account',on_delete=models.PROTECT)
    draft_definition=models.JSONField()
    paused=models.BooleanField(default=False)
    class Meta:
        ordering=['-updated_at','id']
        constraints=[tenant_identity_constraint()]
class FormVersion(TenantRecord):
    form=models.ForeignKey(Form,on_delete=models.PROTECT,related_name='versions')
    number=models.PositiveIntegerField()
    definition=models.JSONField()
    published_by=models.ForeignKey('accounts.Account',on_delete=models.PROTECT)
    class Meta:
        ordering=['-number']
        constraints=[tenant_identity_constraint(),models.UniqueConstraint(fields=['form','number'],name='form_version_number')]
