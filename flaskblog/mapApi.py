import os

try:
    import googlemaps
except ImportError:  # optional: web/demo installs can skip the paid Maps client
    googlemaps = None

API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY') or os.environ.get('API_KEY')

map_client = googlemaps.Client(API_KEY) if (API_KEY and googlemaps) else None
