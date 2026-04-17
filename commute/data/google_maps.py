import os
from typing import Optional
from datetime import datetime

import requests

from commute.config import GOOGLE_MAPS_BASE, MIT_SLOAN_ADDRESS, MIT_SLOAN_LAT, MIT_SLOAN_LON

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")
OUTSCRAPER_API_KEY = os.getenv("OUTSCRAPER_API_KEY", "")


def geocode_address(address: str) -> Optional[tuple[float, float]]:
    if not GOOGLE_MAPS_API_KEY:
        return _geocode_nominatim(address)

    resp = requests.get(
        f"{GOOGLE_MAPS_BASE}/geocode/json",
        params={"address": address, "key": GOOGLE_MAPS_API_KEY},
        timeout=8,
    )
    resp.raise_for_status()
    results = resp.json().get("results", [])
    if not results:
        return None
    loc = results[0]["geometry"]["location"]
    return loc["lat"], loc["lng"]


def _geocode_nominatim(address: str) -> Optional[tuple[float, float]]:
    resp = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": address, "format": "json", "limit": 1},
        headers={"User-Agent": "MIT-Sloan-Commute-Planner/1.0"},
        timeout=8,
    )
    resp.raise_for_status()
    results = resp.json()
    if not results:
        return None
    return float(results[0]["lat"]), float(results[0]["lon"])


def _parse_duration_seconds(leg: dict) -> int:
    duration = leg.get("duration_in_traffic") or leg.get("duration") or {}
    return duration.get("value", 0)


def get_directions(
    origin: str,
    destination: str = MIT_SLOAN_ADDRESS,
    mode: str = "transit",
    departure_time: Optional[int] = None,
) -> Optional[dict]:
    if not GOOGLE_MAPS_API_KEY:
        return _get_directions_outscraper(origin, destination, mode)

    params = {
        "origin": origin,
        "destination": destination,
        "mode": mode,
        "key": GOOGLE_MAPS_API_KEY,
    }
    if departure_time:
        params["departure_time"] = departure_time
    elif mode in ("transit", "driving"):
        params["departure_time"] = "now"

    if mode == "transit":
        params["transit_mode"] = "subway|bus|rail"

    resp = requests.get(f"{GOOGLE_MAPS_BASE}/directions/json", params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    if data.get("status") != "OK":
        return {"error": data.get("status"), "message": data.get("error_message", "")}

    route = data["routes"][0]
    leg = route["legs"][0]
    duration_sec = _parse_duration_seconds(leg)

    steps = []
    for step in leg.get("steps", []):
        transit = step.get("transit_details", {})
        step_info = {
            "instruction": step.get("html_instructions", "").replace("<b>", "").replace("</b>", ""),
            "duration_min": round(step["duration"]["value"] / 60, 1),
            "distance": step["distance"]["text"],
            "mode": step["travel_mode"],
        }
        if transit:
            line = transit.get("line", {})
            step_info["line"] = line.get("short_name") or line.get("name", "")
            step_info["vehicle"] = line.get("vehicle", {}).get("type", "")
            step_info["departure_stop"] = transit.get("departure_stop", {}).get("name", "")
            step_info["arrival_stop"] = transit.get("arrival_stop", {}).get("name", "")
        steps.append(step_info)

    return {
        "source": "Google Maps",
        "mode": mode,
        "duration_min": round(duration_sec / 60, 1),
        "distance": leg["distance"]["text"],
        "departure_time": leg.get("departure_time", {}).get("text", ""),
        "arrival_time": leg.get("arrival_time", {}).get("text", ""),
        "summary": route.get("summary", ""),
        "steps": steps,
        "warnings": route.get("warnings", []),
    }


def _get_directions_outscraper(origin: str, destination: str, mode: str) -> Optional[dict]:
    if not OUTSCRAPER_API_KEY:
        return {"error": "no_credentials", "message": "Set GOOGLE_MAPS_API_KEY or OUTSCRAPER_API_KEY"}

    mode_map = {"transit": "transit", "walking": "walking", "bicycling": "bicycling", "driving": "driving"}
    resp = requests.get(
        "https://api.app.outscraper.com/maps/directions",
        params={
            "origin": origin,
            "destination": destination,
            "travelMode": mode_map.get(mode, "transit"),
        },
        headers={"X-API-KEY": OUTSCRAPER_API_KEY},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()

    if not data.get("data"):
        return {"error": "no_results", "source": "Outscraper"}

    result = data["data"][0] if isinstance(data["data"], list) else data["data"]
    duration_text = result.get("duration", "")
    distance_text = result.get("distance", "")

    duration_min = None
    if duration_text:
        parts = duration_text.replace("hours", "h").replace("hour", "h").replace("mins", "min").replace("min", "min")
        total = 0
        if "h" in parts:
            h, rest = parts.split("h", 1)
            total += int(h.strip()) * 60
            parts = rest
        if "min" in parts:
            total += int(parts.replace("min", "").strip())
        duration_min = total

    return {
        "source": "Google Maps (Outscraper)",
        "mode": mode,
        "duration_min": duration_min,
        "distance": distance_text,
        "steps": result.get("steps", []),
    }


def get_all_routes(origin: str) -> dict:
    results = {}
    for mode in ["transit", "walking", "bicycling"]:
        try:
            results[mode] = get_directions(origin, mode=mode)
        except Exception as e:
            results[mode] = {"error": str(e)}
    return results
