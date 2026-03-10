import requests

def get_weather(city, state):
    API_KEY = "a2b002602129dc21ab0935cab87ef027" # Replace with your real OpenWeatherMap key
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city},{state}&appid={API_KEY}&units=metric"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        if response.status_code == 200:
            # OpenWeatherMap only provides 'rain' key if it is currently raining
            rain_val = data.get('rain', {}).get('1h', 0)
            return {
                "temp": data['main']['temp'],
                "humidity": data['main']['humidity'],
                "description": data['weather'][0]['description'],
                "rain": rain_val
            }
        return None
    except:
        return None