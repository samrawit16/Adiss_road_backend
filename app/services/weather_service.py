from datetime import date
from urllib.parse import urlencode
from urllib.request import urlopen
import json


ADDIS_SUBCITY_COORDINATES = {
    "Bole": (8.9955, 38.7890),
    "Yeka": (9.0400, 38.8200),
    "Kirkos": (9.0000, 38.7600),
    "Arada": (9.0350, 38.7500),
    "Lideta": (9.0100, 38.7350),
    "Nifas Silk-Lafto": (8.9550, 38.7100),
    "Kolfe Keranio": (9.0100, 38.6800),
    "Gullele": (9.0800, 38.7200),
    "Akaki Kaliti": (8.8800, 38.7900),
    "Addis Ketema": (9.0300, 38.7350),
}


WEATHER_CODE_MAP = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def get_weather(
    sub_city: str,
    selected_date: str,
    selected_time: str,
) -> dict:
    coordinates = ADDIS_SUBCITY_COORDINATES.get(sub_city)

    if coordinates is None:
        raise ValueError(
            f"Weather location is not available for sub-city: {sub_city}"
        )

    latitude, longitude = coordinates

    target_date = date.fromisoformat(selected_date)
    today = date.today()

    if target_date < today:
        base_url = "https://archive-api.open-meteo.com/v1/archive"
    else:
        base_url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": (
            "weather_code,"
            "temperature_2m,"
            "precipitation,"
            "cloud_cover,"
            "relative_humidity_2m,"
            "wind_speed_10m"
        ),
        "start_date": selected_date,
        "end_date": selected_date,
        "timezone": "Africa/Addis_Ababa",
    }

    url = f"{base_url}?{urlencode(params)}"

    try:
        with urlopen(url, timeout=15) as response:
            data = json.loads(
                response.read().decode("utf-8")
            )
    except Exception as exc:
        raise RuntimeError(
            "Unable to retrieve weather data for the selected "
            "location and time."
        ) from exc

    hourly = data.get("hourly", {})
    times = hourly.get("time", [])

    if not times:
        raise RuntimeError(
            "The weather service returned no hourly data."
        )

    selected_hour = selected_time[:5]

    index = None

    for i, value in enumerate(times):
        if value[-5:] == selected_hour:
            index = i
            break

    if index is None:
        selected_hour_only = selected_time[:2]

        for i, value in enumerate(times):
            if value[-5:-3] == selected_hour_only:
                index = i
                break

    if index is None:
        raise RuntimeError(
            f"No weather data found for "
            f"{selected_date} {selected_time}."
        )

    weather_code = _value_at(
        hourly.get("weather_code"),
        index,
    )

    weather_code = (
        int(weather_code)
        if weather_code is not None
        else None
    )

    return {
        "weather": WEATHER_CODE_MAP.get(
            weather_code,
            "Unknown",
        ),
        "temperature_c": _number_at(
            hourly.get("temperature_2m"),
            index,
        ),
        "precipitation_mm": _number_at(
            hourly.get("precipitation"),
            index,
        ),
        "cloud_cover_percent": _number_at(
            hourly.get("cloud_cover"),
            index,
        ),
        "humidity_percent": _number_at(
            hourly.get("relative_humidity_2m"),
            index,
        ),
        "wind_speed_kmh": _number_at(
            hourly.get("wind_speed_10m"),
            index,
        ),
        "source": "Open-Meteo",
        "sub_city": sub_city,
        "date": selected_date,
        "time": selected_time,
    }


def _value_at(values, index):
    if not values or index >= len(values):
        return None

    return values[index]


def _number_at(values, index):
    value = _value_at(values, index)

    if value is None:
        return None

    return float(value)