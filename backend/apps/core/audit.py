from .models import AuditEvent

def audit(actor,action,object_type,object_id,changes):
    safe={key:value for key,value in changes.items() if not any(word in key.lower() for word in ['password','token','secret'])}
    return AuditEvent.objects.using('control' if actor.tenant_id is None else 'default').create(tenant_id=actor.tenant_id,actor_id=actor.account_id,action=action,object_type=object_type,object_id=object_id,changes=safe)
