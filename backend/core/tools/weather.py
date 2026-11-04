
import logging
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
import json

logger = logging.getLogger(__name__)

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

REQUEST_TIMEOUT = 15


class WeatherError(Exception):
    """Raised when weather information cannot be retrieved."""


WEATHER_CODES = {
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
    71: "Slight snowfall",
    73: "Moderate snowfall",
    75: "Heavy snowfall",
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


def _get_json(url: str, params: dict) -> dict:
    """Make a bounded-time HTTP GET request and return JSON."""

    request_url = f"{url}?{urlencode(params)}"

    request = Request(
        request_url,
        headers={"User-Agent": "NexusAI/1.0"},
    )

    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            data = json.loads(response.read().decode("utf-8"))

    except HTTPError as error:
        logger.warning("Weather API HTTP error: %s", error.code)
        raise WeatherError(
            f"Weather service returned HTTP {error.code}."
        ) from error

    except (URLError, TimeoutError, OSError) as error:
        logger.exception("Weather API connection failed.")
        raise WeatherError(
            "Could not connect to the weather service. Please try again."
        ) from error

    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise WeatherError(
            "Weather service returned an invalid response."
        ) from error

    if not isinstance(data, dict) or data.get("error"):
        reason = data.get("reason", "Unknown API error") if isinstance(data, dict) else "Invalid response"
        raise WeatherError(f"Weather service error: {reason}")

    return data


def get_weather(location: str, forecast_days: int = 3) -> dict:
    """
    Retrieve current weather and a short daily forecast for a city.

    Args:
        location: City or location name.
        forecast_days: Number of forecast days (1-7).

    Returns:
        Structured weather information.
    """

    if not isinstance(location, str) or not location.strip():
        raise WeatherError("Please specify a city or location.")

    location = location.strip()

    if len(location) < 2 or len(location) > 100:
        raise WeatherError("Location must contain between 2 and 100 characters.")

    if not isinstance(forecast_days, int) or not 1 <= forecast_days <= 7:
        raise WeatherError("Forecast days must be between 1 and 7.")

    # 1. Convert city name into geographic coordinates.
    geo_data = _get_json(
        GEOCODING_URL,
        {
            "name": location,
            "count": 5,
            "language": "en",
            "format": "json",
        },
    )

    locations = geo_data.get("results", [])

    if not locations:
        raise WeatherError(
            f"Could not find the location '{location}'. "
            "Please check the city name."
        )

    # Use the best matching result returned by Open-Meteo.
    place = locations[0]

    latitude = place.get("latitude")
    longitude = place.get("longitude")

    if latitude is None or longitude is None:
        raise WeatherError("Could not resolve the location coordinates.")

    # 2. Retrieve current conditions and daily forecast.
    forecast_data = _get_json(
        FORECAST_URL,
        {
            "latitude": latitude,
            "longitude": longitude,
            "current": (
                "temperature_2m,"
                "relative_humidity_2m,"
                "apparent_temperature,"
                "is_day,"
                "precipitation,"
                "weather_code,"
                "wind_speed_10m,"
                "wind_direction_10m"
            ),
            "daily": (
                "weather_code,"
                "temperature_2m_max,"
                "temperature_2m_min,"
                "precipitation_sum,"
                "precipitation_probability_max,"
                "sunrise,"
                "sunset"
            ),
            "forecast_days": forecast_days,
            "timezone": "auto",
            "temperature_unit": "celsius",
            "wind_speed_unit": "kmh",
        },
    )

    current = forecast_data.get("current", {})
    current_units = forecast_data.get("current_units", {})
    daily = forecast_data.get("daily", {})
    daily_units = forecast_data.get("daily_units", {})

    if not current:
        raise WeatherError("Current weather data is unavailable.")

    weather_code = current.get("weather_code")

    forecast = []

    dates = daily.get("time", [])

    for index, date in enumerate(dates):
        code = daily.get("weather_code", [])

        forecast.append({
            "date": date,
            "condition": WEATHER_CODES.get(
                code[index], "Unknown"
            ) if index < len(code) else "Unknown",
            "temperature_max": (
                daily.get("temperature_2m_max", [])[index]
                if index < len(daily.get("temperature_2m_max", []))
                else None
            ),
            "temperature_min": (
                daily.get("temperature_2m_min", [])[index]
                if index < len(daily.get("temperature_2m_min", []))
                else None
            ),
            "precipitation": (
                daily.get("precipitation_sum", [])[index]
                if index < len(daily.get("precipitation_sum", []))
                else None
            ),
            "precipitation_probability": (
                daily.get("precipitation_probability_max", [])[index]
                if index < len(daily.get("precipitation_probability_max", []))
                else None
            ),
            "sunrise": (
                daily.get("sunrise", [])[index]
                if index < len(daily.get("sunrise", []))
                else None
            ),
            "sunset": (
                daily.get("sunset", [])[index]
                if index < len(daily.get("sunset", []))
                else None
            ),
        })

    return {
        "success": True,
        "provider": "Open-Meteo",
        "location": {
            "name": place.get("name"),
            "admin1": place.get("admin1"),
            "country": place.get("country"),
            "timezone": forecast_data.get("timezone"),
            "latitude": latitude,
            "longitude": longitude,
        },
        "current": {
            "time": current.get("time"),
            "temperature": current.get("temperature_2m"),
            "temperature_unit": current_units.get("temperature_2m", "°C"),
            "feels_like": current.get("apparent_temperature"),
            "humidity": current.get("relative_humidity_2m"),
            "wind_speed": current.get("wind_speed_10m"),
            "wind_speed_unit": current_units.get("wind_speed_10m", "km/h"),
            "wind_direction": current.get("wind_direction_10m"),
            "precipitation": current.get("precipitation"),
            "condition": WEATHER_CODES.get(
                weather_code, "Unknown"
            ),
            "is_day": current.get("is_day"),
        },
        "forecast": forecast,
        "source": "https://open-meteo.com/",
    }
