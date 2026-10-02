"""Ruoli e permessi (SPEC §4). Politica unica usata da UI e API."""

from enum import StrEnum


class Role(StrEnum):
    ADMIN = "ADMIN"  # Amministratore azienda
    RESPONSABILE = "RESPONSABILE"  # Responsabile mangimificio
    OPERATORE = "OPERATORE"
    VETERINARIO = "VETERINARIO"  # Veterinario / consulente
    AUDITOR = "AUDITOR"  # Auditor / ente di controllo


class Permission(StrEnum):
    MASTERDATA_READ = "masterdata:read"
    MASTERDATA_WRITE = "masterdata:write"
    IMPORT_RUN = "import:run"
    USERS_MANAGE = "users:manage"
    AUDIT_READ = "audit:read"


_ALL = frozenset(Permission)

_ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.ADMIN: _ALL,
    Role.RESPONSABILE: frozenset(
        {
            Permission.MASTERDATA_READ,
            Permission.MASTERDATA_WRITE,
            Permission.IMPORT_RUN,
            Permission.AUDIT_READ,
        }
    ),
    # Operatore: nessuna modifica ad anagrafiche critiche.
    Role.OPERATORE: frozenset({Permission.MASTERDATA_READ}),
    Role.VETERINARIO: frozenset({Permission.MASTERDATA_READ}),
    Role.AUDITOR: frozenset({Permission.MASTERDATA_READ, Permission.AUDIT_READ}),
}


def permissions_for(role: Role) -> frozenset[Permission]:
    return _ROLE_PERMISSIONS[role]


def has_permission(role: Role, permission: Permission) -> bool:
    return permission in _ROLE_PERMISSIONS[role]
