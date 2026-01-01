from flask import Flask, request, jsonify
from datetime import datetime, timezone
from skyfield import almanac
from skyfield.api import wgs84, load

app = Flask(__name__)

# Load ephemeris data
ts = load.timescale()
print("Load bsp")
eph = load('de421.bsp')
print("Done loading bsp")

@app.route('/')
def hello_world():
    return 'Hello, World!'

# HTTP GET endpoint that accepts the following query parameters:
# - `date`: The date for which to retrieve the sunrise and sunset times.
#           The format must be an ISO timestamp.
#           If left out the current time is used.
# - `latitude`: The latitude of the location for which to retrieve the sunrise and sunset times.
# - `longitude`: The longitude of the location for which to retrieve the sunrise and sunset times.
# Returns a json object with the following keys:
# - `sunrise`: The time of sunrise.
# - `sunset`: The time of sunset.
@app.route('/astronomy/sun')
def sun():
    try:
        # Get query parameters
        date_param = request.args.get('date')
        latitude = request.args.get('latitude', type=float)
        longitude = request.args.get('longitude', type=float)

        # Validate required parameters
        if latitude is None:
            return jsonify({'error': 'latitude parameter is required'}), 400
        if longitude is None:
            return jsonify({'error': 'longitude parameter is required'}), 400

        # Validate latitude and longitude ranges
        if not (-90 <= latitude <= 90):
            return jsonify({'error': 'latitude must be between -90 and 90'}), 400
        if not (-180 <= longitude <= 180):
            return jsonify({'error': 'longitude must be between -180 and 180'}), 400

        # Parse date or use current time
        if date_param:
            try:
                dt = datetime.fromisoformat(date_param.replace('Z', '+00:00'))
            except ValueError:
                return jsonify({'error': 'Invalid date format. Use ISO 8601 format'}), 400
        else:
            dt = datetime.now(timezone.utc)

        # Ensure datetime is timezone-aware
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        # Create location
        location = wgs84.latlon(latitude, longitude)

        # Define the search window (the day containing the given datetime)
        t0 = ts.from_datetime(dt.replace(hour=0, minute=0, second=0, microsecond=0))
        t1 = ts.from_datetime(dt.replace(hour=23, minute=59, second=59, microsecond=999999))

        # Find sunrise and sunset times
        t, y = almanac.find_discrete(t0, t1, almanac.sunrise_sunset(eph, location))

        sunrise_time = None
        sunset_time = None

        for ti, yi in zip(t, y):
            if yi:  # yi == 1 means sunrise
                sunrise_time = ti.utc_iso()
            else:  # yi == 0 means sunset
                sunset_time = ti.utc_iso()

        result = {}
        if sunrise_time:
            result['sunrise'] = sunrise_time
        if sunset_time:
            result['sunset'] = sunset_time

        if not sunrise_time and not sunset_time:
            # Check if sun is always up or always down
            sun = eph['sun']
            earth = eph['earth']
            observer = earth + location
            t_check = ts.from_datetime(dt)
            astrometric = observer.at(t_check).observe(sun)
            alt, az, distance = astrometric.apparent().altaz()

            if alt.degrees > 0:
                result['message'] = 'Sun is above horizon all day (polar day)'
            else:
                result['message'] = 'Sun is below horizon all day (polar night)'

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500
