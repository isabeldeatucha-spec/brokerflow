import math
import os
from typing import Optional

import requests

from commute.config import PASSIO_BASE_URL, MIT_SLOAN_LAT, MIT_SLOAN_LON

_SESSION = requests.Session()
_SESSION.headers.update({"Accept": "application/json"})


def _haversine_miles(lat1, lon1, lat2, lon2) -> float:
    R = 3958.8
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi, dlambda = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def get_routes() -> list[dict]:
    resp = _SESSION.get(f"{PASSIO_BASE_URL}/routes", timeout=8)
    resp.raise_for_status()
    data = resp.json()
    return data if isinstance(data, list) else data.get("routes", data.get("data", []))


def get_stops() -> list[dict]:
    resp = _SESSION.get(f"{PASSIO_BASE_URL}/stops", timeout=8)
    resp.raise_for_status()
    data = resp.json()
    return data if isinstance(data, list) else data.get("stops", data.get("data", []))


def find_nearby_shuttle_stops(lat: float, lon: float, max_results: int = 3) -> list[dict]:
    stops = get_stops()
    results = []

    for stop in stops:
        slat = stop.get("latitude") or stop.get("lat") or stop.get("position", {}).get("lat")
        slon = stop.get("longitude") or stop.get("lon") or stop.get("position", {}).get("lng")
        if slat is None or slon is None:
            continue

        dist = _haversine_miles(lat, lon, float(slat), float(slon))
        results.append({
            "id": stop.get("id") or stop.get("stopId"),
            "name": stop.get("name") or stop.get("stopName", "Unknown Stop"),
            "lat": float(slat),
            "lon": float(slon),
            "distance_miles": round(dist, 2),
            "walk_minutes": round(dist / 3.0 * 60, 1),
        })

    results.sort(key=lambda x: x["distance_miles"])
    return results[:max_results]


def get_stop_eta(stop_id: str) -> list[dict]:
    resp = _SESSION.get(f"{PASSIO_BASE_URL}/stopETA", params={"stopId": stop_id}, timeout=8)
    resp.raise_for_status()
    data = resp.json()
    etas = data if isinstance(data, list) else data.get("etas", data.get("data", []))

    results = []
    for eta in etas:
        minutes = eta.get("minutesUntilArrival") or eta.get("eta") or eta.get("minutes")
        route_name = eta.get("routeName") or eta.get("route", {}).get("name", "MIT Shuttle")
        if minutes is not None:
            results.append({
                "route": route_name,
                "minutes_away": int(minutes),
            })

    return sorted(results, key=lambda x: x["minutes_away"])


def get_shuttle_options(origin_lat: float, origin_lon: float) -> list[dict]:
    try:
        nearby_stops = find_nearby_shuttle_stops(origin_lat, origin_lon, max_results=3)
        options = []

        for stop in nearby_stops:
            try:
                etas = get_stop_eta(stop["id"])
                for eta in etas[:2]:
                    total = stop["walk_minutes"] + eta["minutes_away"] + 10
                    options.append({
                        "mode": "MIT Shuttle",
                        "origin_stop": stop["name"],
                        "walk_to_stop_min": stop["walk_minutes"],
                        "shuttle_in_min": eta["minutes_away"],
                        "route": eta["route"],
                        "total_est_min": round(total, 0),
                    })
            except Exception:
                continue

        return options
    except Exception as e:
        return [{"mode": "MIT Shuttle", "error": str(e)}]
