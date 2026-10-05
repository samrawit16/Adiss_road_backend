import threading
from pathlib import Path

import joblib
import pandas as pd

from app.services.weather_service import get_weather


BASE_DIR = Path(__file__).resolve().parents[2]

MODEL_PATH = (
    BASE_DIR
    / "models"
    / "aa_guardian_severity_model.joblib"
)


class SeverityPredictionService:
    """Loads the model the first time it is needed, not at start-up.

    The model needs about 190 MB of RAM. Loading it on demand keeps the API small for the many
    requests that never use it (login, reports, notifications), which matters on free hosting
    with only 512 MB of RAM.
    """

    _LAZY = frozenset({"model", "fatal_threshold", "classes", "feature_names", "target_name"})

    def __init__(self):
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Severity model not found at: {MODEL_PATH}"
            )
        self._load_lock = threading.Lock()

    def _load(self) -> None:
        with self._load_lock:
            if "model" in self.__dict__:
                return

            saved_model = joblib.load(MODEL_PATH)
            model = saved_model["model"]

            try:  # one worker is plenty for single predictions and avoids extra threads
                model.steps[-1][1].n_jobs = 1
            except Exception:  # noqa: BLE001
                pass

            self.fatal_threshold = saved_model["fatal_threshold"]
            self.classes = saved_model["classes"]
            self.feature_names = saved_model["feature_names"]
            self.target_name = saved_model["target_name"]
            self.model = model  # set last: its presence means "fully loaded"

    def __getattr__(self, name):
        # Only called when normal lookup fails, i.e. before the model has been loaded.
        if name in self._LAZY:
            self._load()
            return self.__dict__[name]
        raise AttributeError(name)

    def predict(self, input_data: dict) -> dict:
        data = input_data.copy()

       
        sub_city = data.get("Area_accident_occured")
        selected_date = data.get("Date")
        selected_time = data.get("Time")

        if not sub_city:
            raise ValueError(
                "A sub-city is required for the risk prediction."
            )

        if not selected_date:
            raise ValueError(
                "A date is required for the risk prediction."
            )

        if not selected_time:
            raise ValueError(
                "A time is required for the risk prediction."
            )

       
        weather_data = get_weather(
            sub_city=sub_city,
            selected_date=selected_date,
            selected_time=selected_time,
        )

        weather_description = weather_data["weather"]

    
        data["Weather_conditions"] = self._normalize_weather_for_model(
            weather_description
        )

        
        data.pop("Number_of_casualties", None)

       
        for feature in self.feature_names:
            if feature not in data:
                data[feature] = None

        # Keep only features used during training.
        data = {
            feature: data[feature]
            for feature in self.feature_names
        }

        df = pd.DataFrame([data])

        
        probabilities_array = self.model.predict_proba(df)[0]

        probabilities = {
            class_name: float(probability)
            for class_name, probability in zip(
                self.classes,
                probabilities_array,
            )
        }

        prediction = self.model.predict(df)[0]

     
        fatal_probability = probabilities.get(
            "Fatal injury",
            0.0,
        )

        if fatal_probability >= self.fatal_threshold:
            prediction = "Fatal injury"

       
        hour = data.get("Hour")

        is_peak_hour = False
        peak_period = "Off-peak"
        peak_message = None

        if hour is not None:
            hour = int(hour)

            if 7 <= hour < 9:
                is_peak_hour = True
                peak_period = "Morning peak"
                peak_message = (
                    "Higher traffic activity is expected "
                    "during the morning peak."
                )

            elif 16 <= hour < 18:
                is_peak_hour = True
                peak_period = "Evening peak"
                peak_message = (
                    "Higher traffic activity is expected "
                    "during the evening peak."
                )

       
        return {
            "predicted_severity": prediction,
            "probabilities": probabilities,
            "fatal_probability": fatal_probability,
            "fatal_threshold": self.fatal_threshold,

            "sub_city": sub_city,

           
            "weather": weather_description,

           
            "temperature_c": weather_data.get("temperature_c"),
            "precipitation_mm": weather_data.get("precipitation_mm"),
            "cloud_cover_percent": weather_data.get(
                "cloud_cover_percent"
            ),
            "humidity_percent": weather_data.get(
                "humidity_percent"
            ),
            "wind_speed_kmh": weather_data.get(
                "wind_speed_kmh"
            ),

            "light_conditions": data.get(
                "Light_conditions"
            ),

            "is_peak_hour": is_peak_hour,
            "peak_period": peak_period,
            "peak_message": peak_message,
        }

    def _normalize_weather_for_model(
        self,
        weather: str,
    ) -> str:
        """
        Convert the weather description returned by the weather
        provider into a category that is more suitable for the
        trained accident-severity model.

        The displayed weather remains the original human-readable
        weather description.
        """

        value = weather.lower().strip()

        if any(
            word in value
            for word in (
                "thunder",
                "rain",
                "drizzle",
                "shower",
            )
        ):
            return "Raining"

        if any(
            word in value
            for word in (
                "fog",
                "mist",
            )
        ):
            return "Fog or mist"

        if any(
            word in value
            for word in (
                "snow",
                "snowy",
            )
        ):
            return "Snow"

        if any(
            word in value
            for word in (
                "cloud",
                "overcast",
            )
        ):
            return "Cloudy"

        if any(
            word in value
            for word in (
                "wind",
            )
        ):
            return "Windy"

        # Clear / mainly clear weather.
        return "Normal"


severity_prediction_service = SeverityPredictionService()