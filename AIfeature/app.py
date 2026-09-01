"""Wildfire prevention advisor, powered by an explainable risk model."""

import json
import re
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)


def fetch_json(base_url, parameters):
    """Fetch a small JSON response from a public data service."""
    url = f"{base_url}?{urlencode(parameters)}"
    try:
        with urlopen(url, timeout=8) as response:
            return json.loads(response.read().decode("utf-8"))
    except (URLError, TimeoutError, json.JSONDecodeError) as error:
        raise ValueError("Live weather is unavailable right now. Try again shortly.") from error


def bounded_number(value, low, high, label):
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{label} must be a number.")
    if not low <= number <= high:
        raise ValueError(f"{label} must be between {low} and {high}.")
    return number


def assess_risk(data):
    """Estimate fire risk from common fire-weather indicators.

    The transparent weighted model is deliberately easy to audit: it combines
    heat, low humidity, wind, dry vegetation, drought, and nearby ignition
    sources into a 0-100 prevention-priority score.
    """
    temperature = bounded_number(data.get("temperature"), -30, 60, "Temperature")
    humidity = bounded_number(data.get("humidity"), 0, 100, "Humidity")
    wind = bounded_number(data.get("wind_speed"), 0, 160, "Wind speed")
    dryness = bounded_number(data.get("vegetation_dryness"), 0, 100, "Vegetation dryness")
    drought = bounded_number(data.get("drought_index"), 0, 100, "Drought index")
    ignition = bounded_number(data.get("ignition_risk"), 0, 100, "Ignition-source risk")

    heat = max(0, min(100, (temperature - 10) * 2))
    low_humidity = 100 - humidity
    wind_factor = min(100, wind * 2.5)
    score = round(
        0.18 * heat
        + 0.20 * low_humidity
        + 0.18 * wind_factor
        + 0.22 * dryness
        + 0.14 * drought
        + 0.08 * ignition
    )

    if score >= 75:
        level, color = "Extreme", "#b91c1c"
        actions = [
            "Avoid all outdoor burning and postpone equipment that can spark.",
            "Alert local fire officials and prepare evacuation and communication plans.",
            "Patrol high-risk areas and remove fine fuels near buildings immediately.",
        ]
    elif score >= 50:
        level, color = "High", "#ea580c"
        actions = [
            "Create or refresh a 5-foot noncombustible zone around structures.",
            "Clear dry leaves, pine needles, and brush; keep access roads open.",
            "Avoid parking hot vehicles on dry grass and secure chains on trailers.",
        ]
    elif score >= 25:
        level, color = "Moderate", "#ca8a04"
        actions = [
            "Keep hoses, tools, and emergency contacts ready.",
            "Mow only in the cool morning and remove cut vegetation.",
            "Check local fire restrictions before using grills or fire pits.",
        ]
    else:
        level, color = "Low", "#15803d"
        actions = [
            "Maintain defensible space and clear roofs and gutters regularly.",
            "Store firewood and flammable materials away from structures.",
            "Review your household wildfire plan before fire-weather conditions change.",
        ]

    factors = sorted(
        [
            ("Vegetation dryness", dryness * 0.22),
            ("Low humidity", low_humidity * 0.20),
            ("Wind", wind_factor * 0.18),
            ("Heat", heat * 0.18),
            ("Drought", drought * 0.14),
            ("Ignition sources", ignition * 0.08),
        ],
        key=lambda item: item[1], reverse=True,
    )
    return {
        "score": score,
        "level": level,
        "color": color,
        "actions": actions,
        "top_factors": [name for name, contribution in factors[:3] if contribution > 0],
    }


def chat_reply(message):
    """Return a concise, safety-first natural-language reply without an API key."""
    text = message.strip().lower()
    if not text:
        raise ValueError("Please type a question for FireWise AI.")

    if any(word in text for word in ("emergency", "fire nearby", "evacu", "smoke", "flames")):
        return (
            "If there is an active fire, smoke, or an evacuation warning, do not rely on this tool. "
            "Follow official emergency alerts, leave immediately if instructed, and call emergency services when safe."
        )
    if any(word in text for word in ("grill", "barbecue", "bbq", "fire pit", "campfire", "burn")):
        return (
            "Check your local fire restrictions before using any open flame. During dry, windy, or high-risk conditions, "
            "skip burning and use an electric or gas alternative only when local rules allow it."
        )
    if any(word in text for word in ("defensible", "yard", "brush", "vegetation", "plants", "garden")):
        return (
            "Start closest to the building: remove dry leaves and needles, use noncombustible material in the first 5 feet, "
            "and trim or space plants so flames cannot easily travel toward the structure."
        )
    if any(word in text for word in ("evacuation", "evacuate", "leave", "plan")):
        return (
            "Make a two-route evacuation plan, pack medications and documents, keep your vehicle fueled, and sign up for local alerts. "
            "When officials issue an evacuation order, leave promptly."
        )
    if any(word in text for word in ("risk", "weather", "wind", "hot", "humidity", "dry")):
        numbers = [float(value) for value in re.findall(r"\d+(?:\.\d+)?", text)]
        if numbers:
            return (
                "I can assess exact conditions with the prevention-priority form above. "
                "Enter temperature, humidity, wind, vegetation dryness, drought, and ignition-source risk for a tailored score."
            )
        return (
            "Hot, dry, and windy weather raises wildfire risk, especially where vegetation is dry. "
            "Use the assessment form above for a tailored prevention-priority score."
        )
    return (
        "I can help with wildfire prevention, defensible space, safe outdoor activities, evacuation readiness, and fire-weather risk. "
        "Try asking: “How do I make my yard safer?” or “Is a fire pit a good idea today?”"
    )


def live_weather(location):
    location = location.strip()
    if not location:
        raise ValueError("Enter a city or place name to get live weather.")
    geocoding = fetch_json(
        "https://geocoding-api.open-meteo.com/v1/search",
        {"name": location, "count": 1, "language": "en", "format": "json"},
    )
    results = geocoding.get("results", [])
    if not results:
        raise ValueError("Location not found. Try a city and country or state.")
    place = results[0]
    weather = fetch_json(
        "https://api.open-meteo.com/v1/forecast",
        {
            "latitude": place["latitude"],
            "longitude": place["longitude"],
            "current": "temperature_2m,relative_humidity_2m,wind_speed_10m",
            "wind_speed_unit": "kmh",
        },
    )["current"]
    name = ", ".join(part for part in (place.get("name"), place.get("admin1"), place.get("country")) if part)
    return {
        "location": name,
        "temperature": weather["temperature_2m"],
        "humidity": weather["relative_humidity_2m"],
        "wind_speed": weather["wind_speed_10m"],
        "observed_at": weather.get("time"),
        "source": "Open-Meteo weather data",
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.post("/api/assess")
def api_assess():
    data = request.get_json(silent=True) or request.form
    try:
        return jsonify(assess_risk(data))
    except ValueError as error:
        return jsonify({"error": str(error)}), 400


@app.post("/api/chat")
def api_chat():
    data = request.get_json(silent=True) or request.form
    try:
        return jsonify({"reply": chat_reply(data.get("message", ""))})
    except ValueError as error:
        return jsonify({"error": str(error)}), 400


@app.post("/api/live-weather")
def api_live_weather():
    data = request.get_json(silent=True) or request.form
    try:
        return jsonify(live_weather(data.get("location", "")))
    except ValueError as error:
        return jsonify({"error": str(error)}), 400


if __name__ == "__main__":
    app.run(debug=True)
