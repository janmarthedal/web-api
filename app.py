from flask import Flask, request, jsonify
from datetime import datetime, timedelta
from skyfield import almanac
from skyfield.api import wgs84, load
from timezonefinder import TimezoneFinder
import pytz

app = Flask(__name__)

# Load ephemeris data
ts = load.timescale()
eph = load('de421.bsp')

@app.route('/')
def hello_world():
    return 'Hello, World!'

# HTTP GET endpoint that accepts the following query parameters:
# - `lat`: The latitude of the location for which to retrieve the sunrise and sunset times.
# - `lng`: The longitude of the location for which to retrieve the sunrise and sunset times.
# - `timezone`: The time zone to use for both input and output dates and times.
#               Optional, default is the time zone based on the supplied position.
# - `day`: The day for which to retrieve the times. The format must be YYYYMMDD.
#          Optional, default is the current day.
# Returns a json object with the following times, if available:
# - `timezone`: Time zone used for all timestamps.
# - `sunrise`: Object with sunrise times:
# -   `astronomical`: Time of astronomical sunrise.
# -   `nautical`: Time of nautical sunrise.
# -   `civil`: Time of civil sunrise.
# -   `full`: Time of apparent sunrise.
# - `sunset`: Object with sunset times:
# -   `full`: Time of apparent sunset.
# -   `civil`: Time of civil sunset.
# -   `nautical`: Time of nautical sunset.
# -   `astronomical`: Time of astronomical sunset.
@app.route('/astronomy/sun')
def sun():
    try:
        # Get query parameters
        latitude = request.args.get('lat', type=float)
        longitude = request.args.get('lng', type=float)
        timezone_param = request.args.get('timezone')
        day_param = request.args.get('day')

        # Validate required parameters
        if latitude is None:
            return jsonify({'error': 'lat parameter is required'}), 400
        if longitude is None:
            return jsonify({'error': 'lng parameter is required'}), 400

        # Validate latitude and longitude ranges
        if not (-90 <= latitude <= 90):
            return jsonify({'error': 'lat must be between -90 and 90'}), 400
        if not (-180 <= longitude <= 180):
            return jsonify({'error': 'lng must be between -180 and 180'}), 400

        # Determine timezone
        if timezone_param:
            try:
                tz = pytz.timezone(timezone_param)
            except pytz.exceptions.UnknownTimeZoneError:
                return jsonify({'error': f'Unknown timezone: {timezone_param}'}), 400
        else:
            # Use timezonefinder to get timezone from coordinates
            tf = TimezoneFinder()
            timezone_str = tf.timezone_at(lat=latitude, lng=longitude)
            if timezone_str is None:
                return jsonify({'error': 'Could not determine timezone for location'}), 400
            tz = pytz.timezone(timezone_str)

        # Parse day or use current day
        if day_param:
            try:
                if len(day_param) != 8 or not day_param.isdigit():
                    return jsonify({'error': 'day must be in YYYYMMDD format'}), 400
                year = int(day_param[0:4])
                month = int(day_param[4:6])
                day = int(day_param[6:8])
                dt = tz.localize(datetime(year, month, day, 0, 0, 0))
            except (ValueError, pytz.exceptions.AmbiguousTimeError, pytz.exceptions.NonExistentTimeError) as e:
                return jsonify({'error': f'Invalid day: {str(e)}'}), 400
        else:
            dt = datetime.now(tz)

        # Create location
        location = wgs84.latlon(latitude, longitude)

        # Define the search window (full day in the local timezone)
        start_of_day = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1, microseconds=-1)

        t0 = ts.from_datetime(start_of_day)
        t1 = ts.from_datetime(end_of_day)

        # Use dark_twilight_day to find all twilight transitions in one call
        f = almanac.dark_twilight_day(eph, location)
        times, events = almanac.find_discrete(t0, t1, f)

        # Map event codes to twilight phases
        # 0 = Dark (night, sun below -18°)
        # 1 = Astronomical twilight (sun between -18° and -12°)
        # 2 = Nautical twilight (sun between -12° and -6°)
        # 3 = Civil twilight (sun between -6° and -0.833°)
        # 4 = Day (sun above -0.833°)
        PHASE_TO_KEY = {
            1: 'astronomical',
            2: 'nautical',
            3: 'civil',
            4: 'full',
        }

        prev_phase = 0
        sunrise = {}
        sunset = {}

        # Process events to extract twilight times
        for ti, phase in zip(times, events):
            time_str = ti.astimezone(tz).strftime('%Y-%m-%dT%H:%M:%S')
            if phase > prev_phase:
                sunrise[PHASE_TO_KEY[phase]] = time_str
            else:
                sunset[PHASE_TO_KEY[prev_phase]] = time_str
            prev_phase = phase

        result = {
            'timezone': str(tz),
            'sunrise': sunrise,
            'sunset': sunset,
        }

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500
