# Web Api

A Flask-based web API for astronomical calculations.

## Endpoints

### GET /astronomy/sun

Calculate sunrise, sunset, and twilight times for a given date and location.

#### Query Parameters

- `lat` (required): The latitude of the location (-90 to 90)
- `lng` (required): The longitude of the location (-180 to 180)
- `timezone` (optional): The time zone to use for both input and output dates and times (e.g., "America/New_York", "Europe/London"). If omitted, the timezone is automatically determined based on the supplied position.
- `day` (optional): The day for which to retrieve the times in YYYYMMDD format (e.g., "20240115"). If omitted, uses the current day.

#### Response

Returns a JSON object with the following fields (all times are in ISO 8601 format with the specified timezone):

- `timezone`: The time zone used for all timestamps
- `astro_up`: Time of astronomical sunrise (sun at -18°)
- `nautical_up`: Time of nautical sunrise (sun at -12°)
- `civil_up`: Time of civil sunrise (sun at -6°)
- `up`: Time of apparent sunrise (sun's upper limb at horizon)
- `down`: Time of apparent sunset (sun's upper limb at horizon)
- `civil_down`: Time of civil sunset (sun at -6°)
- `nautical_down`: Time of nautical sunset (sun at -12°)
- `astro_down`: Time of astronomical sunset (sun at -18°)

Note: In polar regions or during extreme seasons, some or all twilight events may not occur on a given day.

#### Examples

**New York on January 15, 2024:**
```bash
curl "http://localhost:5000/astronomy/sun?lat=40.7128&lng=-74.0060&day=20240115"
```

Response:
```json
{
  "timezone": "America/New_York",
  "astro_up": "2024-01-15T05:45:23-0500",
  "nautical_up": "2024-01-15T06:18:45-0500",
  "civil_up": "2024-01-15T06:50:12-0500",
  "up": "2024-01-15T07:18:07-0500",
  "down": "2024-01-15T16:52:50-0500",
  "civil_down": "2024-01-15T17:20:45-0500",
  "nautical_down": "2024-01-15T17:52:12-0500",
  "astro_down": "2024-01-15T18:25:34-0500"
}
```

**London (current date with explicit timezone):**
```bash
curl "http://localhost:5000/astronomy/sun?lat=51.5074&lng=-0.1278&timezone=Europe/London"
```

**Tokyo on a specific day:**
```bash
curl "http://localhost:5000/astronomy/sun?lat=35.6762&lng=139.6503&day=20240621"
```

**Polar region (may have missing events):**
```bash
curl "http://localhost:5000/astronomy/sun?lat=78.2232&lng=15.6267&day=20240621"
```

Response (during polar day):
```json
{
  "timezone": "Arctic/Longyearbyen"
}
```

## Running the Application

```bash
# Install dependencies
uv sync

# Run in development mode
flask --app app run

# Or with gunicorn
gunicorn app:app
```

## Dependencies

- Flask: Web framework
- Skyfield: Astronomical calculations
- timezonefinder: Automatic timezone detection from coordinates
- pytz: Timezone handling
- gunicorn: WSGI HTTP server