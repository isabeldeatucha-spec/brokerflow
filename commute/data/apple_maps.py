import os
import time
from typing import Optional

import requests

from commute.config import APPLE_MAPS_BASE, MIT_SLOAN_LAT, MIT_SLOAN_LON

APPLE_MAPS_KEY_ID = os.getenv("APPLE_MAPS_KEY_ID", "")
APPLE_TEAM_ID = os.getenv("APPLE_TEAM_ID", "")
APPLE_PRIVATE_KEY = os.getenv("APPLE_MAPS_PRIVATE_KEY", "")

_cached_token: Optional[str] = None
_token_expiry: float = 0.0


def _get_auth_token() -> Optional[str]:
    global _cached_token, _token_expiry

    if not all([APPLE_MAPS_KEY_ID, APPLE_TEAM_ID, APPLE_PRIVATE_KEY]):
        return None

    if _cached_token and time.time() < _token_expiry - 60:
        return _cached_token

    try:
        import jwt
    except ImportError:
        return None

    now = int(time.time())
    payload = {"iss": APPLE_TEAM_ID, "iat": now, "exp": now + 3600}
    headers = {"kid": APPLE_MAPS_KEY_ID, "alg": "ES256"}
    private_key = APPLE_PRIVATE_KEY.replace("\\n", "\n")

    _cached_token = jwt.encode(payload, private_key, algorithm="ES256", headers=headers)
    _token_expiry = now + 3600
    return _cached_token


def get_directions(
    origin_lat: float,
    origin_lon: float,
    dest_lat: float = MIT_SLOAN_LAT,
    dest_lon: float = MIT_SLOAN_LON,
    transport_type: str = "Transit",
) -> Optional[dict]:
    token = _get_auth_token()
    if not token:
        return {"error": "no_credentials", "message": "Set APPLE_MAPS_KEY_ID, APPLE_TEAM_ID, APPLE_MAPS_PRIVATE_KEY"}

    params = {
        "origin": f"{origin_lat},{origin_lon}",
        "destination": f"{dest_lat},{dest_lon}",
        "transportType": transport_type,
        "departureDate": "now",
    }

    resp = requests.get(
        f"{APPLE_MAPS_BASE}/directions",
        params=params,
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()

    routes = data.get("routes", [])
    if not routes:
        return {"error": "no_routes", "source": "Apple Maps"}

    route = routes[0]
    legs = route.get("legs", [])
    total_duration_sec = sum(leg.get("durationSeconds", 0) for leg in legs)
    total_distance_m = sum(leg.get("distanceMeters", 0) for leg in legs)

    steps = []
    for leg in legs:
        for step in leg.get("steps", []):
            steps.append({
                "instruction": step.get("instructions", ""),
                "duration_min": round(step.get("durationSeconds", 0) / 60, 1),
                "distance_m": step.get("distanceMeters", 0),
                "mode": step.get("transportType", transport_type),
            })

    return {
        "source": "Apple Maps",
        "transport_type": transport_type,
        "duration_min": round(total_duration_sec / 60, 1),
        "distance_miles": round(total_distance_m * 0.000621371, 2),
        "steps": steps,
    }


def get_all_routes(origin_lat: float, origin_lon: float) -> dict:
    results = {}
    for mode in ["Transit", "Walking", "Automobile"]:
        try:
            results[mode] = get_directions(origin_lat, origin_lon, transport_type=mode)
        except Exception as e:
            results[mode] = {"error": str(e)}
    return results
