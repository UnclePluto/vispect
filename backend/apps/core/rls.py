import re

def apply_tenant_rls(table_name: str) -> list[str]:
    if not re.fullmatch(r'[a-z][a-z0-9_]*',table_name):
        raise ValueError('非法表名')
    t = f'"{table_name}"'
    predicate = "tenant_id = NULLIF(current_setting('vispect.tenant_id',true),'')::uuid"
    return [
        f'ALTER TABLE {t} ENABLE ROW LEVEL SECURITY',
        f'ALTER TABLE {t} FORCE ROW LEVEL SECURITY',
        f'CREATE POLICY tenant_scope ON {t} TO vispect_app,vispect_owner USING ({predicate}) WITH CHECK ({predicate})',
        f'GRANT SELECT,INSERT,UPDATE,DELETE ON {t} TO vispect_app',
        f'REVOKE ALL ON {t} FROM vispect_control',
    ]
