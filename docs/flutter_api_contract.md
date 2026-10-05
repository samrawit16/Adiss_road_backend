# Flutter API contract

Base URL: `/api/v1`

## Safety context

`POST /safety/context`

Body:
- `latitude`: double
- `longitude`: double
- `activity`: `walking | cycling | driving | passenger | unknown`
- `speed_kmh`: optional double
- `phone_use`: bool

Use this response for the always-visible safety card:
- `road_name`
- `speed_limit_kmh`
- `speed_limit_source`
- `speed_warning`
- `phone_use_warning`
- `safety_message`

Do not display a made-up speed limit when `speed_limit_kmh` is `null`.

## Safety event

`POST /safety/events` with bearer token.

Use when the Flutter app wants to record a detected/declared phone-use or speed warning.

## Nearby authority

`GET /safety/authorities?latitude=<lat>&longitude=<lon>&radius_km=50`

## Accident report

`POST /safety/accident-reports` with bearer token.

The Flutter app should take the current GPS reading immediately before submitting the report and include:
- latitude
- longitude
- gps_accuracy_m
- occurred_at
- report_type
- severity
- injuries_reported
- emergency_required
- description
- evidence_urls

The backend stores the submitted coordinates. It does not attempt to infer a different location.
