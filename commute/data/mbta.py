import math
import os
from datetime import datetime, timezone
from typing import Optional

import requests

from commute.config import MBTA_API_BASE, MBTA_ROUTE_TYPE_NAMES, MIT_SLOAN_LAT, MIT_SLOAN_LON

_HEADERS = {"x-api-key": os.getenv("MBTA_API_KEY", "")} if os.getenv("MBTA_API_KEY") else {}


def _haversine_miles(lat1, lon1, lat2, lon2) -> float:
    R = 3958.8
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def find_nearby_stops(lat: float, lon: float, radius_miles: float = 0.4, route_types: list[int] = None) -> list[dict]:
    params = {
        "filter[latitude]": lat,
        "filter[longitude]": lon,
        "filter[radius]": radius_miles / 69.0,
        "sort": "distance",
        "page[limit]": 20,
    }
    if route_types:
        params["filter[route_type]"] = ",".join(str(t) for t in route_types)

    resp = requests.get(f"{MBTA_API_BASE}/stops", params=params, headers=_HEADERS, timeout=8)
    resp.raise_for_status()

    stops = []
    for s in resp.json().get("data", []):
        attr = s["attributes"]
        slat, slon = attr.get("latitude"), attr.get("longitude")
        distance = _haversine_miles(lat, lon, slat, slon) if slat and slon else 999
        stops.append({
            "id": s["id"],
            "name": attr["name"],
            "lat": slat,
            "lon": slon,
            "distance_miles": round(distance, 2),
            "walk_minutes": round(distance / 3.0 * 60, 1),
        })
    return stops


def get_predictions_for_stop(stop_id: str, route_types: list[int] = None, limit: int = 5) -> list[dict]:
    params = {
        "filter[stop]": stop_id,
        "sort": "departure_time",
        "include": "route,trip",
        "page[limit]": limit * 3,
    }
    if route_types:
        params["filter[route_type]"] = ",".join(str(t) for t in route_types)

    resp = requests.get(f"{MBTA_API_BASE}/predictions", params=params, headers=_HEADERS, timeout=8)
    resp.raise_for_status()
    payload = resp.json()

    route_map = {r["id"]: r for r in payload.get("included", []) if r["type"] == "route"}

    predictions = []
    now = datetime.now(timezone.utc)
    for p in payload.get("data", []):
        attr = p["attributes"]
        dep = attr.get("departure_time") or attr.get("arrival_time")
        if not dep:
            continue
        dep_dt = datetime.fromisoformat(dep)
        minutes_away = round((dep_dt - now).total_seconds() / 60, 1)
        if minutes_away < 0:
            continue

        route_id = p["relationships"].get("route", {}).get("data", {}).get("id", "")
        route_data = route_map.get(route_id, {})
        route_attr = route_data.get("attributes", {})
        route_type = route_attr.get("type", -1)

        predictions.append({
            "route_id": route_id,
            "route_name": route_attr.get("long_name") or route_attr.get("short_name") or route_id,
            "route_type": MBTA_ROUTE_TYPE_NAMES.get(route_type, "Transit"),
            "departure_time": dep_dt.strftime("%I:%M %p"),
            "minutes_away": minutes_away,
            "direction": attr.get("direction_id"),
            "status": attr.get("status", ""),
        })

        if len(predictions) >= limit:
            break

    return predictions


def get_transit_options(origin_lat: float, origin_lon: float) -> dict:
    results = {"subway": [], "bus": [], "commuter_rail": []}
    try:
        subway_stops = find_nearby_stops(origin_lat, origin_lon, radius_miles=0.5, route_types=[1])
        for stop in subway_stops[:2]:
            preds = get_predictions_for_stop(stop["id"], route_types=[1], limit=3)
            for p in preds:
                p["origin_stop"] = stop["name"]
                p["walk_to_stop_min"] = stop["walk_minutes"]
                p["total_to_kendall"] = None
            results["subway"].append({"stop": stop, "predictions": preds})
    except Exception:
        pass

    try:
        bus_stops = find_nearby_stops(origin_lat, origin_lon, radius_miles=0.3, route_types=[3])
        for stop in bus_stops[:3]:
            preds = get_predictions_for_stop(stop["id"], route_types=[3], limit=2)
            for p in preds:
                p["origin_stop"] = stop["name"]
                p["walk_to_stop_min"] = stop["walk_minutes"]
            results["bus"].append({"stop": stop, "predictions": preds})
    except Exception:
        pass

    try:
        cr_stops = find_nearby_stops(origin_lat, origin_lon, radius_miles=1.0, route_types=[2])
        for stop in cr_stops[:2]:
            preds = get_predictions_for_stop(stop["id"], route_types=[2], limit=3)
            for p in preds:
                p["origin_stop"] = stop["name"]
                p["walk_to_stop_min"] = stop["walk_minutes"]
            results["commuter_rail"].append({"stop": stop, "predictions": preds})
    except Exception:
        pass

    return results
