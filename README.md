# Web Api

A Flask-based web API for astronomical calculations.

## Endpoints

### GET /astronomy/sun

Calculate sunrise and sunset times for a given date and location.

#### Query Parameters

- `latitude` (required): The latitude of the location (-90 to 90)
- `longitude` (required): The longitude of the location (-180 to 180)
- `date` (optional): ISO 8601 formatted timestamp. If omitted, uses current time.

#### Response

Returns a JSON object with:
- `sunrise`: ISO 8601 timestamp of sunrise (if applicable)
- `sunset`: ISO 8601 timestamp of sunset (if applicable)
- `message`: Explanation for polar regions where sun doesn't rise/set on the given day

#### Examples

**New York on January 15, 2024:**
```bash
curl "http://localhost:5000/astronomy/sun?date=2024-01-15T12:00:00Z&latitude=40.7128&longitude=-74.0060"
```

Response:
```json
{
  "sunrise": "2024-01-15T12:18:07Z",
  "sunset": "2024-01-15T21:52:50Z"
}
```

**London (current date):**
```bash
curl "http://localhost:5000/astronomy/sun?latitude=51.5074&longitude=-0.1278"
```

**Polar day (North Pole in summer):**
```bash
curl "http://localhost:5000/astronomy/sun?date=2024-06-21T12:00:00Z&latitude=89&longitude=0"
```

Response:
```json
{
  "message": "Sun is above horizon all day (polar day)"
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
