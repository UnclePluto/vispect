from dataclasses import dataclass
from uuid import UUID

@dataclass(frozen=True)
class Actor:
    account_id: UUID
    tenant_id: UUID | None
    role: str
    doctor_id: UUID | None = None
