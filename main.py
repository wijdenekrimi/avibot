import math
import os
import sys
import requests
import time
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Load credentials from environment variables
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
OPENSKY_USERNAME = os.getenv('OPENSKY_USERNAME', '')
OPENSKY_PASSWORD = os.getenv('OPENSKY_PASSWORD', '')

if not TELEGRAM_TOKEN:
    sys.exit('TELEGRAM_TOKEN environment variable is required.')

# Haversine formula to calculate distance between two points on Earth
def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    r = 6371  # Radius of earth in kilometers
    return c * r

def fetch_flights():
    """
    Fetch flight data from OpenSky Network API.
    Normalizes the response into the same structure used by the rest of the bot.
    Retries up to 3 times on failure.
    """
    url = "https://opensky-network.org/api/states/all"
    retry_count = 3
    for attempt in range(retry_count):
        try:
            auth = None
            if OPENSKY_USERNAME and OPENSKY_PASSWORD:
                auth = (OPENSKY_USERNAME, OPENSKY_PASSWORD)
            response = requests.get(url, auth=auth, timeout=10)
            response.raise_for_status()
            data = response.json()
            states = data.get('states', []) or []

            flights = []
            for state in states:
                longitude = state[5]
                latitude = state[6]
                if longitude is None or latitude is None:
                    continue

                callsign = (state[1] or '').strip()
                if not callsign:
                    callsign = 'Unknown'

                # Convert units: altitude in meters, speed from m/s to km/h
                altitude = state[7] if state[7] is not None else 'Unknown'

                speed = 'Unknown'
                if state[9] is not None:
                    speed = round(state[9] * 3.6)  # m/s to km/h

                flights.append({
                    'aircraft': {'iata': 'Unknown', 'model': 'Unknown'},
                    'airline': {'name': callsign},
                    'flight': {'iata': callsign},
                    'live': {
                        'latitude': latitude,
                        'longitude': longitude,
                        'altitude': altitude,
                        'speed_horizontal': speed,
                    },
                    'additional': {
                        'icao24': state[0],
                        'origin_country': state[2] or 'Unknown',
                        'on_ground': state[8],
                        'heading': state[10] if state[10] is not None else 'Unknown',
                        'vertical_rate': state[11] if state[11] is not None else 'Unknown',
                    },
                })
            return flights
        except requests.RequestException as e:
            if attempt < retry_count - 1:
                print(f"Attempt {attempt + 1} failed: {e}, retrying in 1 second...")
                time.sleep(1)
            else:
                print(f"All {retry_count} attempts failed: {e}")
                return []

# Handler for /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_markup = ReplyKeyboardMarkup(
        [[KeyboardButton(text="Share Location", request_location=True)]],
        one_time_keyboard=False,
        resize_keyboard=True
    )
    await update.message.reply_text(
        "Welcome to the Aviation Radar Bot! Share your location to get nearby flights.",
        reply_markup=reply_markup
    )

# Handler for location messages
async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_location = update.message.location
    user_lat = float(user_location.latitude)
    user_lon = float(user_location.longitude)

    # Fetch flight data
    flights = fetch_flights()

    # Calculate distances and filter flights with live data
    flight_distances = []
    for flight in flights:
        live = flight.get('live')
        if live and 'latitude' in live and 'longitude' in live:
            try:
                flight_lat = float(live['latitude'])
                flight_lon = float(live['longitude'])
            except (TypeError, ValueError):
                continue
            distance = haversine_distance(user_lat, user_lon, flight_lat, flight_lon)
            flight_distances.append((distance, flight))

    # Sort by distance and take top 10
    closest_flights = sorted(flight_distances, key=lambda x: x[0])[:10]

    if not closest_flights:
        await update.message.reply_text("No nearby flights found.")
        return

    # Format response
    response = "Nearby Flights:\n\n"
    for distance, flight in closest_flights:
        aircraft = flight.get('aircraft', {})
        airline = flight.get('airline', {})
        flight_info = flight.get('flight', {})
        live = flight.get('live', {})
        additional = flight.get('additional', {})

        aircraft_type = aircraft.get('iata', 'Unknown')
        model = aircraft.get('model', 'Unknown')
        altitude = live.get('altitude', 'Unknown')
        speed = live.get('speed_horizontal', 'Unknown')
        airline_name = airline.get('name', 'Unknown')
        flight_number = flight_info.get('iata', 'Unknown')
        origin_country = additional.get('origin_country', 'Unknown')
        on_ground = "Yes" if additional.get('on_ground') else "No"
        heading = additional.get('heading', 'Unknown')
        vertical_rate = additional.get('vertical_rate', 'Unknown')
        icao24 = additional.get('icao24', 'Unknown')
        profile_link = f"https://map.opensky-network.org/?icao={icao24}"

        response += f"Distance: {distance:.2f} km\n"
        response += f"Aircraft Type: {aircraft_type}\n"
        response += f"Model: {model}\n"
        response += f"Altitude: {altitude} m\n"
        response += f"Speed: {speed} km/h\n"
        response += f"Airline: {airline_name}\n"
        response += f"Flight Number: {flight_number}\n"
        response += f"Origin Country: {origin_country}\n"
        response += f"On Ground: {on_ground}\n"
        response += f"Heading: {heading}°\n"
        response += f"Vertical Rate: {vertical_rate} m/s\n"
        response += f"Flight Profile: {profile_link}\n\n"

    await update.message.reply_text(response)

# Main function
def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.LOCATION, handle_location))

    application.run_polling()

if __name__ == '__main__':
    main()