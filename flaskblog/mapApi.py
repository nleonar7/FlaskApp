import os
from pprint import pprint
import googlemaps #pip install googlemaps

API_KEY = 'AIzaSyDRB64l8RHUXuIxhVH1IyBg1Vhh9aGqT9U'#os.environ.get('API_KEY')
map_client = googlemaps.Client(API_KEY)

'''
def get_longitute_latitude(address):
    response = map_client.geocode(address)
    pprint(response[0])#['geometry'])

get_longitute_latitude('241 84 street Brooklyn, NY')

'''