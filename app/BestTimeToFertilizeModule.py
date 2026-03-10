import os
import requests
from dotenv import load_dotenv

load_dotenv()


class BestTimeToFertilize:

    def __init__(self, city_name, state_name, api_key=None):
        self.city = city_name
        self.state = state_name
        self.weather_data = {}
        self.daily_forecast = []
        self.api_success = False
        # ✅ reads from .env, never hardcoded
        self.api_key = api_key or os.environ.get("OPENWEATHER_API_KEY", "")

    def api_caller(self):
        API_KEY = self.api_key

        print("🌍 Weather API HIT for city:", self.city)

        current_url = (
            f"https://api.openweathermap.org/data/2.5/weather"
            f"?q={self.city},IN&appid={API_KEY}&units=metric"
        )

        # ── BLOCK 1: Current Weather (separate try so it always saves) ──
        try:
            response = requests.get(current_url, timeout=10)
            data = response.json()

            print("RAW CURRENT WEATHER →", data)

            if "main" not in data:
                print(f"❌ Current weather failed for city: {self.city} | Response: {data}")
                self.api_success = False
                return

            self.weather_data = data
            self.api_success = True
            print("✅ Current Weather SUCCESS")

        except Exception as e:
            print(f"❌ Current weather fetch error for '{self.city}':", e)
            self.api_success = False
            return  # No point fetching forecast if current weather failed

        # ── BLOCK 2: 5-Day Forecast (free API, replaces deprecated onecall) ──
        try:
            forecast_url = (
                f"https://api.openweathermap.org/data/2.5/forecast"
                f"?q={self.city},IN&appid={API_KEY}&units=metric&cnt=40"
            )

            forecast_response = requests.get(forecast_url, timeout=10)
            forecast_data = forecast_response.json()

            print("RAW 5-DAY FORECAST →", forecast_data)

            if "list" not in forecast_data:
                print(f"⚠️ Forecast unavailable for '{self.city}', using current weather only.")
                self.daily_forecast = []
                return

            # Convert 3-hour blocks into daily rain totals
            daily_map = {}
            for item in forecast_data["list"]:
                date = item["dt_txt"].split(" ")[0]  # e.g. "2026-02-24"
                rain = item.get("rain", {}).get("3h", 0)
                if date not in daily_map:
                    daily_map[date] = {"rain": 0}
                daily_map[date]["rain"] += rain

            # Store as list of dicts sorted by date
            self.daily_forecast = [
                {"date": d, "rain": v["rain"]}
                for d, v in sorted(daily_map.items())
            ]

            print("✅ 5-Day Forecast SUCCESS →", self.daily_forecast)

        except Exception as e:
            print(f"⚠️ Forecast fetch error for '{self.city}':", e)
            self.daily_forecast = []  # Non-fatal — current weather still works

    # --------------------------------------------------
    def is_api_call_success(self):
        return self.api_success

    # --------------------------------------------------
    def best_time_fertilize(self):

        if not self.api_success:
            return ("error", "Weather Error", "Unable to fetch weather data")

        temp = self.weather_data["main"]["temp"]
        humidity = self.weather_data["main"]["humidity"]
        rainfall = self.weather_data.get("rain", {}).get("1h", 0)

        print("TODAY WEATHER →", temp, humidity, rainfall)

        if rainfall >= 20:  # Fixed: was 200mm (unrealistic), 20mm/hr = heavy rain
            return ("danger", "Not Favorable", "Heavy rainfall detected")

        elif temp < 15:
            return ("warning", "Caution", "Low temperature — fertilizer uptake will be slow")

        else:
            return ("safe", "Optimal", "Safe to fertilize today")

    # --------------------------------------------------
    def seven_day_forecast(self):

        forecast = []

        if not self.daily_forecast:
            return forecast

        for i, day in enumerate(self.daily_forecast[:7]):
            rain = day.get("rain", 0)

            if rain >= 20:
                status = "Not Favorable"
            elif rain >= 8:
                status = "Moderate"
            else:
                status = "Favorable"

            forecast.append({
                "Day": f"Day {i+1}",
                "Date": day.get("date", ""),
                "Status": status,
                "Rain": round(rain, 1)
            })

        print("7-DAY FERTILIZER FORECAST →", forecast)
        return forecast