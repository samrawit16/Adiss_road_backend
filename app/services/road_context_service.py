import json
import logging
import math
import time
import urllib.parse
import urllib.request
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.safety import RoadSpeedLimit

logger = logging.getLogger(__name__)

_CACHE: dict[tuple[float, float], tuple[float, dict[str, Any]]] = {}

CACHE_SECONDS = 45
OSM_RADIUS_METERS = 150
OSM_TIMEOUT_SECONDS = 5


def _distance_km(lat1, lon1, lat2, lon2):
    r = 6371.0088
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)

    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)

    a = (
        math.sin(dp / 2) ** 2
        + math.cos(p1)
        * math.cos(p2)
        * math.sin(dl / 2) ** 2
    )

    return 2 * r * math.asin(math.sqrt(a))


def _parse_speed(value: Any) -> float | None:
    if value is None:
        return None

    text = str(value).strip().lower()

    if not text:
        return None


    for token in text.replace(";", ",").split(","):
        token = token.strip()

        if not token:
            continue

        try:
            if token.endswith("mph"):
                number = token[:-3].strip()
                return round(float(number) * 1.609344, 1)

            if "km/h" in token:
                number = token.replace("km/h", "").strip()
                return float(number)

            number = ""

            for char in token:
                if char.isdigit() or char == ".":
                    number += char

            if number:
                return float(number)

        except (ValueError, TypeError):
            continue

    return None


class RoadContextService:
    def __init__(self, db: Session):
        self.db = db

    def lookup(
        self,
        latitude: float,
        longitude: float,
    ) -> dict[str, Any]:

        key = (
            round(latitude, 4),
            round(longitude, 4),
        )

        cached = _CACHE.get(key)

        if cached:
            cached_at, cached_data = cached

            if time.time() - cached_at < CACHE_SECONDS:
                logger.info(
                    "Road context cache hit: %s",
                    cached_data,
                )
                return cached_data

        

        local = self._lookup_local(
            latitude,
            longitude,
        )

        if local:
            logger.info(
                "Road found in local registry: %s",
                local,
            )

            _CACHE[key] = (
                time.time(),
                local,
            )

            return local

        
        osm = self._lookup_osm(
            latitude,
            longitude,
        )

        if osm:
            logger.info(
                "Road found from OSM: %s",
                osm,
            )

            _CACHE[key] = (
                time.time(),
                osm,
            )

            self._persist_osm(
                latitude,
                longitude,
                osm,
            )

            return osm

        

        result = {
            "road_name": None,
            "highway_type": None,
            "speed_limit_kmh": None,
            "source": None,
        }

        _CACHE[key] = (
            time.time(),
            result,
        )

        logger.warning(
            "No road found near %.6f, %.6f",
            latitude,
            longitude,
        )

        return result

    def _lookup_local(
        self,
        latitude: float,
        longitude: float,
    ) -> dict[str, Any] | None:

        rows = self.db.scalars(
            select(RoadSpeedLimit)
        ).all()

        nearest = None
        nearest_distance = float("inf")

        for row in rows:
            distance = _distance_km(
                latitude,
                longitude,
                row.latitude,
                row.longitude,
            )

            if distance < nearest_distance:
                nearest = row
                nearest_distance = distance

        if (
            nearest is not None
            and nearest_distance <= 0.15
        ):
            return {
                "road_name": nearest.road_name,
                "highway_type": nearest.highway_type,
                "speed_limit_kmh": (
                    float(nearest.speed_limit_kmh)
                    if nearest.speed_limit_kmh is not None
                    else None
                ),
                "source": (
                    nearest.source
                    or "local_road_registry"
                ),
            }

        return None

    def _lookup_osm(
        self,
        latitude: float,
        longitude: float,
    ) -> dict[str, Any] | None:

       
        query = f"""
        [out:json][timeout:5];
        way(
            around:{OSM_RADIUS_METERS},
            {latitude},
            {longitude}
        )["highway"];
        out tags center;
        """

        url = (
            "https://overpass-api.de/api/interpreter?"
            + urllib.parse.urlencode(
                {"data": query}
            )
        )

        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "AAGuardian/1.0",
                "Accept": "application/json",
            },
        )

        try:
            logger.info(
                "Looking up OSM road at %.6f, %.6f",
                latitude,
                longitude,
            )

            with urllib.request.urlopen(
                request,
                timeout=OSM_TIMEOUT_SECONDS,
            ) as response:

                payload = json.loads(
                    response.read().decode("utf-8")
                )

        except Exception as exc:
            logger.warning(
                "OSM lookup failed: %s",
                exc,
            )
            return None

        elements = payload.get(
            "elements",
            [],
        )

        if not elements:
            return None

        best_with_speed = None
        best_with_speed_distance = float("inf")

        best_any = None
        best_any_distance = float("inf")

        for element in elements:

            tags = element.get(
                "tags",
                {},
            )

            center = element.get(
                "center",
                {},
            )

            if (
                "lat" not in center
                or "lon" not in center
            ):
                continue

            highway_type = tags.get(
                "highway"
            )

            # Ignore pedestrian paths, footways, cycleways, etc.
            if highway_type in {
                "footway",
                "path",
                "pedestrian",
                "cycleway",
                "steps",
                "bridleway",
                "corridor",
            }:
                continue

            distance = _distance_km(
                latitude,
                longitude,
                float(center["lat"]),
                float(center["lon"]),
            )

            if distance > 0.15:
                continue

            speed = _parse_speed(
                tags.get("maxspeed")
            )

            candidate = {
                "road_name": (
                    tags.get("name")
                    or tags.get("ref")
                ),
                "highway_type": highway_type,
                "speed_limit_kmh": speed,
                "source": "openstreetmap",
            }

            if distance < best_any_distance:
                best_any_distance = distance
                best_any = candidate

            if (
                speed is not None
                and distance < best_with_speed_distance
            ):
                best_with_speed_distance = distance
                best_with_speed = candidate

        
        if best_with_speed is not None:
            return best_with_speed

        return best_any

    def _persist_osm(
        self,
        latitude: float,
        longitude: float,
        data: dict[str, Any],
    ) -> None:

        if (
            not data.get("road_name")
            or data.get("speed_limit_kmh") is None
        ):
            return

        try:
            row = RoadSpeedLimit(
                road_name=data["road_name"],
                highway_type=data.get(
                    "highway_type"
                ),
                speed_limit_kmh=data[
                    "speed_limit_kmh"
                ],
                latitude=latitude,
                longitude=longitude,
                source=data.get(
                    "source",
                    "openstreetmap",
                ),
            )

            self.db.add(row)
            self.db.commit()

        except Exception as exc:
            logger.warning(
                "Could not save OSM road data: %s",
                exc,
            )
            self.db.rollback()