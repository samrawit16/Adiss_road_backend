from datetime import datetime, timezone
from typing import Annotated

from pydantic import PlainSerializer


def _utc_iso(value: datetime) -> str:
    """The database stores naive UTC. Send it as explicit UTC ("...Z") so every
    client (Flutter, the dashboard, curl) reads the right instant instead of
    guessing that a bare timestamp is local time."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)
    return value.isoformat().replace("+00:00", "Z")


UTCDateTime = Annotated[datetime, PlainSerializer(_utc_iso, return_type=str, when_used="json")]
