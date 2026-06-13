import os
import googlemaps

API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY') or os.environ.get('API_KEY')

map_client = googlemaps.Client(API_KEY) if API_KEY else None
