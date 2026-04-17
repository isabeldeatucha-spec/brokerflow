import json
from datetime import datetime, timezone
from typing import Any

from langchain_core.tools import tool

from commute.data import mbta, bluebike, passio, google_maps, apple_maps, outlook
from commute.config import MIT_SLOAN_ADDRESS


@tool
def get_mbta_options(origin_lat: float, origin_lon: float) -> str:
    """Get real-time MBTA subway, bus, and commuter rail departures near the given coordinates."""
    try:
        results = mbta.get_transit_options(origin_lat, origin_lon)
        summary = []

        for stop_data in results.get("subway", []):
            stop = stop_data["stop"]
            preds = stop_data["predictions"]
            if preds:
                lines = [f"  - {p['route_name']} in {p['minutes_away']}min (departs {p['departure_time']})" for p in preds]
                summary.append(f"🚇 {stop['name']} [{stop['walk_minutes']}min walk]:\n" + "\n".join(lines))

        for stop_data in results.get("bus", []):
            stop = stop_data["stop"]
            preds = stop_data["predictions"]
            if preds:
                lines = [f"  - Route {p['route_id']} in {p['minutes_away']}min" for p in preds]
                summary.append(f"🚌 {stop['name']} [{stop['walk_minutes']}min walk]:\n" + "\n".join(lines))

        for stop_data in results.get("commuter_rail", []):
            stop = stop_data["stop"]
            preds = stop_data["predictions"]
            if preds:
                lines = [f"  - {p['route_name']} at {p['departure_time']} ({p['minutes_away']}min away)" for p in preds]
                summary.append(f"🚂 {stop['name']} [{stop['walk_minutes']}min walk]:\n" + "\n".join(lines))

        return "\n\n".join(summary) if summary else "No MBTA departures found nearby."
    except Exception as e:
        return f"MBTA data unavailable: {e}"


@tool
def get_bluebike_options(origin_lat: float, origin_lon: float) -> str:
    """Get Bluebike availability at nearby stations and estimated cycling time to MIT Sloan."""
    try:
        options = bluebike.get_bike_options(origin_lat, origin_lon)
        if not options or (len(options) == 1 and "error" in options[0]):
            return f"Bluebike data unavailable: {options[0].get('error', 'unknown error')}"

        lines = []
        for opt in options:
            if "error" in opt:
                continue
            lines.append(
                f"🚲 {opt['origin_station']} → {opt['dock_at_mit']}\n"
                f"  Walk to station: {opt['walk_to_station_min']}min | "
                f"Bikes available: {opt['available_bikes']} | "
                f"Ride: {opt['ride_min']}min | "
                f"Total: ~{int(opt['total_min'])}min"
            )
        return "\n\n".join(lines) if lines else "No Bluebike stations available nearby."
    except Exception as e:
        return f"Bluebike data unavailable: {e}"


@tool
def get_shuttle_options(origin_lat: float, origin_lon: float) -> str:
    """Get MIT Shuttle ETAs from nearby stops via Passio GO."""
    try:
        options = passio.get_shuttle_options(origin_lat, origin_lon)
        if not options or (len(options) == 1 and "error" in options[0]):
            return f"MIT Shuttle data unavailable: {options[0].get('error', 'unknown error')}"

        lines = []
        for opt in options:
            if "error" in opt:
                continue
            lines.append(
                f"🚐 MIT Shuttle {opt['route']} from {opt['origin_stop']}\n"
                f"  Walk: {opt['walk_to_stop_min']}min | "
                f"Shuttle arrives in: {opt['shuttle_in_min']}min | "
                f"Total: ~{int(opt['total_est_min'])}min"
            )
        return "\n\n".join(lines) if lines else "No MIT Shuttle service found nearby."
    except Exception as e:
        return f"MIT Shuttle data unavailable: {e}"


@tool
def get_google_maps_routes(origin_address: str) -> str:
    """Get Google Maps routing for transit, walking, and cycling from origin to MIT Sloan."""
    try:
        results = google_maps.get_all_routes(origin_address)
        lines = []

        mode_labels = {"transit": "🚇 Transit", "walking": "🚶 Walking", "bicycling": "🚲 Cycling"}
        for mode, data in results.items():
            label = mode_labels.get(mode, mode)
            if "error" in data:
                lines.append(f"{label}: unavailable ({data['error']})")
                continue
            dep = f" | Departs: {data['departure_time']}" if data.get("departure_time") else ""
            arr = f" | Arrives: {data['arrival_time']}" if data.get("arrival_time") else ""
            lines.append(
                f"{label}: {data['duration_min']}min ({data['distance']}){dep}{arr}"
            )
            if data.get("steps"):
                key_steps = [s for s in data["steps"] if s.get("line") or s.get("mode") == "TRANSIT"][:3]
                for step in key_steps:
                    detail = step.get("line", "") or step.get("mode", "")
                    lines.append(f"   → {detail}: {step.get('departure_stop', '')} → {step.get('arrival_stop', '')}")

        return "\n".join(lines) if lines else "Google Maps routing unavailable."
    except Exception as e:
        return f"Google Maps unavailable: {e}"


@tool
def get_apple_maps_routes(origin_lat: float, origin_lon: float) -> str:
    """Get Apple Maps routing for transit, walking, and driving from origin to MIT Sloan."""
    try:
        results = apple_maps.get_all_routes(origin_lat, origin_lon)
        lines = []

        mode_labels = {"Transit": "🚇 Transit", "Walking": "🚶 Walking", "Automobile": "🚗 Driving"}
        for mode, data in results.items():
            label = mode_labels.get(mode, mode)
            if "error" in data:
                lines.append(f"{label}: unavailable ({data['error']})")
                continue
            lines.append(f"{label}: {data['duration_min']}min ({data['distance_miles']}mi)")

        return "\n".join(lines) if lines else "Apple Maps routing unavailable."
    except Exception as e:
        return f"Apple Maps unavailable: {e}"


@tool
def get_outlook_events(user_email: str = "") -> str:
    """Get today's Outlook calendar events to determine when you need to be at MIT Sloan."""
    try:
        events = outlook.get_today_events(user_email or None)
        if not events:
            return "No upcoming Outlook events found today. (Check AZURE_CLIENT_ID/SECRET/TENANT_ID credentials.)"

        lines = ["📅 Today's upcoming events:"]
        for e in events[:5]:
            mit_tag = " [MIT Sloan]" if e.get("is_mit_sloan") else ""
            loc = f" @ {e['location']}" if e['location'] else ""
            lines.append(f"  {e['start_str']}–{e['end_str']}: {e['subject']}{loc}{mit_tag}")

        return "\n".join(lines)
    except Exception as e:
        return f"Outlook data unavailable: {e}"


ALL_TOOLS = [
    get_mbta_options,
    get_bluebike_options,
    get_shuttle_options,
    get_google_maps_routes,
    get_apple_maps_routes,
    get_outlook_events,
]
