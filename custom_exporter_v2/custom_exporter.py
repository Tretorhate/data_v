import logging
import os
import time
import requests
from prometheus_client import start_http_server, Gauge

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Configuration
# TODO: REMOVE API_KEY BEFORE SUBMISSION!
API_KEY = ""  # Replace with your OpenWeatherMap API key
CITY = "London"
UPDATE_INTERVAL = 20  # seconds
PORT = 8001

# Define at least 10 custom metrics (Gauges for current values)
temperature = Gauge('weather_temperature_celsius', 'Current temperature in Celsius', ['city'])
humidity = Gauge('weather_humidity_percent', 'Current humidity percentage', ['city'])
pressure = Gauge('weather_pressure_hpa', 'Atmospheric pressure in hPa', ['city'])
wind_speed = Gauge('weather_wind_speed_mps', 'Wind speed in m/s', ['city'])
wind_direction = Gauge('weather_wind_direction_deg', 'Wind direction in degrees', ['city'])
cloudiness = Gauge('weather_cloudiness_percent', 'Cloud coverage percentage', ['city'])
visibility = Gauge('weather_visibility_km', 'Visibility in kilometers', ['city'])
rain_volume = Gauge('weather_rain_volume_mm', 'Rain volume in last hour in mm', ['city'])
snow_volume = Gauge('weather_snow_volume_mm', 'Snow volume in last hour in mm', ['city'])
feels_like = Gauge('weather_feels_like_celsius', 'Feels-like temperature in Celsius', ['city'])
uv_index = Gauge('weather_uv_index', 'UV index', ['city'])
sunrise_time = Gauge('weather_sunrise_timestamp', 'Sunrise timestamp (Unix)', ['city'])
sunset_time = Gauge('weather_sunset_timestamp', 'Sunset timestamp (Unix)', ['city'])

def fetch_weather_data():
    """Fetch weather data from OpenWeatherMap API and update metrics"""
    if not API_KEY:
        logger.error("OPENWEATHER_API_KEY not set!")
        return
    
    url = f'https://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={API_KEY}&units=metric'
    
    # Retry logic for network issues
    max_retries = 3
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            # Increased timeout to 30 seconds
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                main = data.get('main', {})
                wind = data.get('wind', {})
                clouds = data.get('clouds', {})
                sys = data.get('sys', {})
                rain = data.get('rain', {'1h': 0})
                snow = data.get('snow', {'1h': 0})
                
                # Set metrics with labels
                temperature.labels(city=CITY).set(main.get('temp', 0))
                humidity.labels(city=CITY).set(main.get('humidity', 0))
                pressure.labels(city=CITY).set(main.get('pressure', 0))
                wind_speed.labels(city=CITY).set(wind.get('speed', 0))
                wind_direction.labels(city=CITY).set(wind.get('deg', 0))
                cloudiness.labels(city=CITY).set(clouds.get('all', 0))
                
                # Visibility is in meters, convert to km
                visibility_meters = data.get('visibility', 0)
                visibility_km = visibility_meters / 1000.0 if visibility_meters > 0 else 0
                visibility.labels(city=CITY).set(visibility_km)
                
                rain_volume.labels(city=CITY).set(rain.get('1h', 0))
                snow_volume.labels(city=CITY).set(snow.get('1h', 0))
                feels_like.labels(city=CITY).set(main.get('feels_like', 0))
                sunrise_time.labels(city=CITY).set(sys.get('sunrise', 0))
                sunset_time.labels(city=CITY).set(sys.get('sunset', 0))
                
                # UV index requires separate API call with One Call API 3.0 (optional)
                # For now, set to 0 if not available in current response
                uv_index.labels(city=CITY).set(0)
                
                logger.info(f"Weather data updated for {CITY}: temp={main.get('temp', 0)}°C, humidity={main.get('humidity', 0)}%")
                return  # Success, exit retry loop
                
            elif response.status_code == 401:
                # Invalid API key - don't retry
                error_data = response.json() if response.text else {}
                logger.error(f"Invalid API key (401). Please check your OPENWEATHER_API_KEY in .env file.")
                logger.error(f"Error message: {error_data.get('message', 'Unauthorized')}")
                logger.error("Get a valid API key from: https://openweathermap.org/api")
                return  # Don't retry on auth errors
                
            elif response.status_code == 404:
                logger.error(f"City '{CITY}' not found (404). Please check the city name.")
                return  # Don't retry on 404
                
            else:
                error_msg = response.text[:200] if response.text else "Unknown error"
                logger.warning(f"API returned status {response.status_code}: {error_msg}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"Failed after {max_retries} attempts")
                    
        except requests.exceptions.ConnectTimeout as e:
            logger.warning(f"Connection timeout to OpenWeatherMap API (attempt {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.error("Connection timeout after all retries. Check your network connection and Docker container network settings.")
                
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"Connection error to OpenWeatherMap API (attempt {attempt + 1}/{max_retries}): {str(e)[:100]}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.error("Connection failed after all retries. The container may not have internet access.")
                logger.error("Check Docker network settings and firewall/proxy configuration.")
                
        except requests.exceptions.Timeout as e:
            logger.warning(f"Request timeout (attempt {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.error("Request timeout after all retries.")
                
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request error (attempt {attempt + 1}/{max_retries}): {str(e)[:100]}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.error(f"Request failed after all retries: {e}")
                
        except KeyError as e:
            logger.exception(f"Error parsing API response - missing key: {e}")
            return  # Don't retry on parsing errors
            
        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
            return  # Don't retry on unexpected errors

def main():
    """Main function to start the exporter"""
    if not API_KEY or API_KEY == "your_api_key_here":
        logger.error("API_KEY not set! Please update API_KEY in custom_exporter.py")
        logger.error("Get your API key from: https://openweathermap.org/api")
        return
    
    # Mask API key in logs (show only first 8 chars)
    masked_key = API_KEY[:8] + "..." if len(API_KEY) > 8 else "***"
    logger.info(f"Starting Weather Exporter on port {PORT} (interval {UPDATE_INTERVAL}s)")
    logger.info(f"Monitoring weather for city: {CITY}")
    logger.info(f"API Key: {masked_key} (masked)")
    
    # Test connection on startup
    logger.info("Testing API connection...")
    fetch_weather_data()
    
    start_http_server(PORT)
    logger.info(f"Exporter running on http://localhost:{PORT}/metrics")
    logger.info("Metrics will be updated every {} seconds".format(UPDATE_INTERVAL))
    
    while True:
        fetch_weather_data()
        time.sleep(UPDATE_INTERVAL)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Exporter interrupted, shutting down")

