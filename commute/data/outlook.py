import os
from datetime import datetime, timezone, timedelta
from typing import Optional

import requests

from commute.config import MICROSOFT_GRAPH_BASE

AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID", "")
AZURE_CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET", "")
AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID", "")
OUTLOOK_USER_EMAIL = os.getenv("OUTLOOK_USER_EMAIL", "")

_token_cache: dict = {}

MIT_SLOAN_KEYWORDS = [
    "mit", "sloan", "e62", "e52", "50 memorial", "kendall",
    "cambridge", "classroom", "lecture", "seminar", "session",
    "class", "study", "group", "office hours",
]


def _get_access_token() -> Optional[str]:
    if not all([AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID]):
        return None

    now = datetime.now(timezone.utc).timestamp()
    if _token_cache.get("token") and _token_cache.get("expires_at", 0) > now + 60:
        return _token_cache["token"]

    resp = requests.post(
        f"https://login.microsoftonline.com/{AZURE_TENANT_ID}/oauth2/v2.0/token",
        data={
            "client_id": AZURE_CLIENT_ID,
            "client_secret": AZURE_CLIENT_SECRET,
            "grant_type": "client_credentials",
            "scope": "https://graph.microsoft.com/.default",
        },
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    _token_cache["token"] = data["access_token"]
    _token_cache["expires_at"] = now + data.get("expires_in", 3600)
    return _token_cache["token"]


def get_today_events(user_email: str = None) -> list[dict]:
    token = _get_access_token()
    if not token:
        return []

    email = user_email or OUTLOOK_USER_EMAIL
    if not email:
        return []

    now = datetime.now(timezone.utc)
    start = now.replace(hour=0, minute=0, second=0).isoformat()
    end = now.replace(hour=23, minute=59, second=59).isoformat()

    resp = requests.get(
        f"{MICROSOFT_GRAPH_BASE}/users/{email}/calendarView",
        params={
            "startDateTime": start,
            "endDateTime": end,
            "$orderby": "start/dateTime",
            "$top": 20,
            "$select": "subject,start,end,location,isAllDay,bodyPreview",
        },
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    resp.raise_for_status()

    events = []
    for e in resp.json().get("value", []):
        if e.get("isAllDay"):
            continue
        start_str = e["start"]["dateTime"]
        end_str = e["end"]["dateTime"]
        start_dt = datetime.fromisoformat(start_str.rstrip("Z")).replace(tzinfo=timezone.utc)
        end_dt = datetime.fromisoformat(end_str.rstrip("Z")).replace(tzinfo=timezone.utc)

        if start_dt < now:
            continue

        events.append({
            "subject": e.get("subject", "Untitled"),
            "start": start_dt,
            "end": end_dt,
            "start_str": start_dt.astimezone().strftime("%I:%M %p"),
            "end_str": end_dt.astimezone().strftime("%I:%M %p"),
            "location": e.get("location", {}).get("displayName", ""),
            "preview": e.get("bodyPreview", "")[:200],
        })

    return events


def get_next_mit_event(user_email: str = None) -> Optional[dict]:
    events = get_today_events(user_email)
    for event in events:
        loc = event["location"].lower()
        subj = event["subject"].lower()
        preview = event["preview"].lower()
        text = f"{loc} {subj} {preview}"

        if any(kw in text for kw in MIT_SLOAN_KEYWORDS):
            return {**event, "is_mit_sloan": True}

    return events[0] if events else None


def get_required_arrival_time(buffer_minutes: int, user_email: str = None) -> Optional[dict]:
    event = get_next_mit_event(user_email)
    if not event:
        return None

    arrival_needed = event["start"] - timedelta(minutes=buffer_minutes)
    return {
        "event_subject": event["subject"],
        "event_start": event["start"],
        "event_start_str": event["start_str"],
        "location": event["location"],
        "arrival_needed": arrival_needed,
        "arrival_needed_str": arrival_needed.astimezone().strftime("%I:%M %p"),
        "buffer_minutes": buffer_minutes,
        "is_mit_sloan": event.get("is_mit_sloan", False),
    }
