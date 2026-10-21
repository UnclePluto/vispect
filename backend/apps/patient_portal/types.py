from dataclasses import dataclass
from uuid import UUID

@dataclass(frozen=True)
class PatientPrincipal:
    tenant_id: UUID
    identity_id: UUID
    session_id: UUID
    session_token: UUID
