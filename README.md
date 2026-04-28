# avibot

A simple Telegram bot that shows nearby live flights based on a user-shared location.

## Features

- Uses the OpenSky Network API to fetch live flight data
- Calculates distance from the user location using the Haversine formula
- Returns up to 10 nearest flights with details such as:
  - aircraft callsign
  - altitude
  - speed
  - origin country
  - heading and vertical rate
  - link to OpenSky flight profile

## Requirements

- Python 3.10+
- `python-telegram-bot`
- `requests`

Install dependencies with:

```bash
pip install -r requirements.txt
```

## Environment Variables

Set the following environment variables before running the bot:

- `TELEGRAM_TOKEN` - Telegram bot token (required)
- `OPENSKY_USERNAME` - OpenSky Network username (optional)
- `OPENSKY_PASSWORD` - OpenSky Network password (optional)

## Running the bot

```bash
python main.py
```

## Usage

1. Start the bot on Telegram with `/start`
2. Share your location using the keyboard button
3. The bot replies with nearby flights and detailed live information

## Notes

- Flight data is fetched from `https://opensky-network.org/api/states/all`
- If authentication is provided, the bot will use OpenSky credentials for the request
- If no flights are found nearby, the bot returns a friendly message

