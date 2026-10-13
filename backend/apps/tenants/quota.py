from dataclasses import dataclass
from django.db import transaction,IntegrityError
from apps.core.context import tenant_transaction
from apps.core.permissions import require_tenant
from apps.core.errors import ApiError
from .models import TenantQuota

RESOURCES=('doctors','patients','studies')
@dataclass(frozen=True)
class UsageCounts:
    doctors:int
    patients:int
    studies:int

def mutate_with_quota(actor,resource,mutation,*,delta=1):
    require_tenant(actor)
    if resource not in RESOURCES or delta not in [-1,0,1]:raise ValueError('非法配额操作')
    try:
        with tenant_transaction(actor.tenant_id):
            quota=TenantQuota.objects.select_for_update().get(tenant_id=actor.tenant_id)
            if delta>0 and getattr(quota,f'{resource}_used')>=getattr(quota,f'{resource}_limit'):
                raise ApiError('quota_exceeded','该类资源数量已达租户上限')
            return mutation()
    except IntegrityError as exc:
        name=getattr(getattr(exc.__cause__,'diag',None),'constraint_name','') or ''
        if name.startswith('quota_exceeded'):
            raise ApiError('quota_exceeded','该类资源数量已达租户上限') from exc
        raise

def quota_trigger_sql(table_name,resource):
    if {'doctors_doctor':'doctors','patients_patient':'patients','studies_study':'studies'}.get(table_name)!=resource:
        raise ValueError('不支持的配额资源表')
    fn=f'vispect_{resource}_quota'
    return [f"""CREATE FUNCTION {fn}() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
    DECLARE change_count integer; target uuid; used_count integer; limit_count integer;
    BEGIN
      target := CASE WHEN TG_OP='DELETE' THEN OLD.tenant_id ELSE NEW.tenant_id END;
      IF target IS DISTINCT FROM NULLIF(current_setting('vispect.tenant_id',true),'')::uuid THEN
        RAISE EXCEPTION 'tenant context rejected' USING ERRCODE='42501';
      END IF;
      IF TG_OP='UPDATE' AND OLD.tenant_id IS DISTINCT FROM NEW.tenant_id THEN
        RAISE EXCEPTION 'tenant cannot change' USING ERRCODE='23514';
      END IF;
      change_count := CASE WHEN TG_OP='INSERT' THEN CASE WHEN NEW.deleted_at IS NULL THEN 1 ELSE 0 END
        WHEN TG_OP='DELETE' THEN CASE WHEN OLD.deleted_at IS NULL THEN -1 ELSE 0 END
        ELSE (CASE WHEN NEW.deleted_at IS NULL THEN 1 ELSE 0 END)-(CASE WHEN OLD.deleted_at IS NULL THEN 1 ELSE 0 END) END;
      IF change_count <> 0 THEN
        SELECT {resource}_used,{resource}_limit INTO used_count,limit_count FROM public.tenants_tenantquota WHERE tenant_id=target FOR UPDATE;
        IF NOT FOUND OR used_count+change_count>limit_count OR used_count+change_count<0 THEN
          RAISE EXCEPTION 'quota exceeded' USING ERRCODE='23514',CONSTRAINT='quota_exceeded_{resource}';
        END IF;
        UPDATE public.tenants_tenantquota SET {resource}_used=used_count+change_count WHERE tenant_id=target;
      END IF;
      IF TG_OP='DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
    END $$""",
    f'REVOKE ALL ON FUNCTION {fn}() FROM PUBLIC',
    f'CREATE TRIGGER resource_quota BEFORE INSERT OR UPDATE OR DELETE ON {table_name} FOR EACH ROW EXECUTE FUNCTION {fn}()']
