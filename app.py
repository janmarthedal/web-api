from flask import Flask, request, jsonify
from datetime import datetime, timedelta
from skyfield import almanac
from skyfield.api import wgs84, load
from timezonefinder import TimezoneFinder
import pytz

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

        print(times)
        print(events)

        # Map event codes to twilight phases
        # 0 = Dark (night, sun below -18°)
        # 1 = Astronomical twilight (sun between -18° and -12°)
        # 2 = Nautical twilight (sun between -12° and -6°)
        # 3 = Civil twilight (sun between -6° and -0.833°)
        # 4 = Day (sun above -0.833°)

        # Initialize all times as None
        astro_up = None
        nautical_up = None
        civil_up = None
        full_up = None
        full_down = None
        civil_down = None
        nautical_down = None
        astro_down = None

        # Process events to extract twilight times
        for ti, event in zip(times, events):
            time_str = ti.astimezone(tz).strftime('%Y-%m-%dT%H:%M:%S%z')

            if event == 1:  # Entering astronomical twilight from dark
                astro_up = time_str
            elif event == 2:  # Entering nautical twilight
                nautical_up = time_str
            elif event == 3:  # Entering civil twilight
                civil_up = time_str
            elif event == 4:  # Entering day (sunrise)
                full_up = time_str
            # Reverse transitions (going back down)
            # When transitioning from higher to lower number, it's a "down" event

        # For sunset events, we need to check transitions in reverse
        # Process again looking for descending transitions
        for i in range(len(events) - 1):
            if events[i] == 4 and events[i + 1] == 3:  # Day to civil twilight (sunset)
                full_down = times[i + 1].astimezone(tz).strftime('%Y-%m-%dT%H:%M:%S%z')
            elif events[i] == 3 and events[i + 1] == 2:  # Civil to nautical
                civil_down = times[i + 1].astimezone(tz).strftime('%Y-%m-%dT%H:%M:%S%z')
            elif events[i] == 2 and events[i + 1] == 1:  # Nautical to astronomical
                nautical_down = times[i + 1].astimezone(tz).strftime('%Y-%m-%dT%H:%M:%S%z')
            elif events[i] == 1 and events[i + 1] == 0:  # Astronomical to dark
                astro_down = times[i + 1].astimezone(tz).strftime('%Y-%m-%dT%H:%M:%S%z')

        # Build response
        sunrise = {}
        if astro_up:
            sunrise['astro'] = astro_up
        if nautical_up:
            sunrise['nautical'] = nautical_up
        if civil_up:
            sunrise['civil'] = civil_up
        if full_up:
            sunrise['full'] = full_up

        sunset = {}
        if full_down:
            sunset['full'] = full_down
        if civil_down:
            sunset['civil'] = civil_down
        if nautical_down:
            sunset['nautical'] = nautical_down
        if astro_down:
            sunset['astro'] = astro_down

        result = {
            'timezone': str(tz),
            'sunrise': sunrise,
            'sunset': sunset,
        }

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500
