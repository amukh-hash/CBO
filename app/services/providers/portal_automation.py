"""Portal automation adapter placeholder.

Safety notes:
- Keep browser automation local only.
- Require explicit user consent for credential storage and automation runs.
- Use dedicated least-privileged browser profile.
"""

from __future__ import annotations

from app.services.providers.base import ProviderAdapter, ProviderRecord
from app.services.providers.registry import registry


class PortalAutomationAdapter(ProviderAdapter):
    name = "portal_automation"

    def refresh(self) -> list[ProviderRecord]:
        return []

    def healthcheck(self) -> dict[str, str]:
        return {"status": "disabled", "adapter": self.name}


registry.register("portal_automation", PortalAutomationAdapter)
