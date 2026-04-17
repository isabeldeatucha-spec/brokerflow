import math
from typing import Optional

import requests

from commute.config import BLUEBIKES_GBFS_BASE, MIT_SLOAN_LAT, MIT_SLOAN_LON

# Approx cycling speed in mph
BIKE_SPEED_MPH = 10.0


def _haversine_miles(lat1, lon1, lat2, lon2) -> float:
    R = 3958.8
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _fetch_stations() -> tuple[list[dict], dict[str, dict]]:
    info_resp = requests.get(f"{BLUEBIKES_GBFS_BASE}/station_information.json", timeout=8)
    info_resp.raise_for_status()
    stations = info_resp.json()["data"]["stations"]

    status_resp = requests.get(f"{BLUEBIKES_GBFS_BASE}/station_status.json", timeout=8)
    status_resp.raise_for_status()
    status_map = {s["station_id"]: s for s in status_resp.json()["data"]["stations"]}

    return stations, status_map


def find_nearest_stations(lat: float, lon: float, max_results: int = 3, min_bikes: int = 1) -> list[dict]:
    stations, status_map = _fetch_stations()
    results = []

    for s in stations:
        dist = _haversine_miles(lat, lon, s["lat"], s["lon"])
        status = status_map.get(s["station_id"], {})
        available_bikes = (
            status.get("num_bikes_available", 0) +
            status.get("num_ebikes_available", 0)
        )
        available_docks = status.get("num_docks_available", 0)
        is_renting = status.get("is_renting", 0)

        results.append({
            "station_id": s["station_id"],
            "name": s["name"],
            "lat": s["lat"],
            "lon": s["lon"],
            "distance_miles": round(dist, 2),
            "walk_to_station_min": round(dist / 3.0 * 60, 1),
            "available_bikes": available_bikes,
            "available_docks": available_docks,
            "is_renting": bool(is_renting),
        })

    results.sort(key=lambda x: x["distance_miles"])
    return [r for r in results if r["available_bikes"] >= min_bikes][:max_results]


def find_nearest_dock_at_mit(max_results: int = 2) -> list[dict]:
    stations, status_map = _fetch_stations()
    results = []

    for s in stations:
        dist = _haversine_miles(MIT_SLOAN_LAT, MIT_SLOAN_LON, s["lat"], s["lon"])
        status = status_map.get(s["station_id"], {})
        available_docks = status.get("num_docks_available", 0)

        results.append({
            "name": s["name"],
            "distance_miles": round(dist, 2),
            "available_docks": available_docks,
        })

    results.sort(key=lambda x: x["distance_miles"])
    return results[:max_results]


def get_bike_options(origin_lat: float, origin_lon: float) -> list[dict]:
    try:
        origin_stations = find_nearest_stations(origin_lat, origin_lon, max_results=3)
        mit_docks = find_nearest_dock_at_mit(max_results=2)

        options = []
        for station in origin_stations:
            ride_dist = _haversine_miles(station["lat"], station["lon"], MIT_SLOAN_LAT, MIT_SLOAN_LON)
            ride_min = round(ride_dist / BIKE_SPEED_MPH * 60, 0)
            walk_last = _haversine_miles(MIT_SLOAN_LAT, MIT_SLOAN_LON, MIT_SLOAN_LAT, MIT_SLOAN_LON)

            total_min = station["walk_to_station_min"] + ride_min + (
                mit_docks[0]["distance_miles"] / 3.0 * 60 if mit_docks else 5
            )

            options.append({
                "mode": "Bluebike",
                "origin_station": station["name"],
                "walk_to_station_min": station["walk_to_station_min"],
                "available_bikes": station["available_bikes"],
                "ride_distance_miles": round(ride_dist, 2),
                "ride_min": int(ride_min),
                "total_min": round(total_min, 0),
                "dock_at_mit": mit_docks[0]["name"] if mit_docks else "MIT Sloan",
                "docks_available": mit_docks[0]["available_docks"] if mit_docks else "?",
            })

        return options
    except Exception as e:
        return [{"mode": "Bluebike", "error": str(e)}]
