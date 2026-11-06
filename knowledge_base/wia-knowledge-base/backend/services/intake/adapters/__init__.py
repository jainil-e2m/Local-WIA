from backend.services.intake.adapters.base import SourceAdapter


def get_adapter(provider: str) -> SourceAdapter:
    """Adapters are the only code that knows a provider's API."""
    if provider == "slack":
        from backend.services.intake.adapters.slack import SlackAdapter
        return SlackAdapter()
    if provider == "clickup":
        from backend.services.intake.adapters.clickup import ClickUpAdapter
        return ClickUpAdapter()
    if provider == "gmail":
        from backend.services.intake.adapters.gmail import GmailAdapter
        return GmailAdapter()
    if provider == "drive":
        from backend.services.intake.adapters.drive import DriveAdapter
        return DriveAdapter()
    if provider == "calendar":
        from backend.services.intake.adapters.calendar import CalendarAdapter
        return CalendarAdapter()
    if provider == "fathom":
        from backend.services.intake.adapters.fathom import FathomAdapter
        return FathomAdapter()
    if provider == "leadlock":
        from backend.services.intake.adapters.leadlock import LeadLockAdapter
        return LeadLockAdapter()
    raise ValueError(f"no adapter for provider {provider!r}")


PROVIDERS = ("slack", "clickup", "gmail", "drive", "calendar", "fathom", "leadlock")
