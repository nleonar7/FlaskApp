from bs4 import BeautifulSoup
import requests

SEARCH_URL = (
    'http://www.greaterbinghamtonmls.com/real-estate/property-search'
    '?lp_l_propertytype_value_many_to_one%5B%5D=Residential'
    '&lp_l_propertytype_value_many_to_one%5B%5D=MultiFamily'
    '&lp_l_propertytype_value_many_to_one%5B%5D=Rental'
    '&lp_l_architecturalstyle_value=All'
    '&lp_l_county_value=Broome'
    '&lp_l_schooldistrict_value%5B%5D=Binghamton'
    '&slider_filter%5Bmin%5D=0&slider_filter%5Bmax%5D=999999999999'
    '&lp_l_bedstotal_value%5Bmin%5D=0&lp_l_bedstotal_value%5Bmax%5D=999999999999'
    '&lp_l_bathstotal_value%5Bmin%5D=0&lp_l_bathstotal_value%5Bmax%5D=999999999999'
    '&lp_l_city_value=&lp_l_livingarea_value=&lp_l_yearbuilt_value='
    '&lp_l_garage_value%5Bmin%5D=0&lp_l_garage_value%5Bmax%5D=999999999999'
    '&lp_l_acrestotal_value%5Bmin%5D=0&lp_l_acrestotal_value%5Bmax%5D=999999999999'
    '&date_filter%5Bvalue%5D%5Byear%5D=&date_filter%5Bvalue%5D%5Bmonth%5D=&date_filter%5Bvalue%5D%5Bday%5D='
    '&lp_l_streetnumber_value=&lp_l_streetname_value=&lp_l_listingid_value='
    '&sortoptions=lp_l_listprice_value+DESC&displayoptions=grid'
)


def gen_title_link():
    source = requests.get(SEARCH_URL, timeout=15).text
    soup = BeautifulSoup(source, 'lxml')
    articles = soup.find_all('div', class_='views-field views-field-title')

    title_link = []
    for div in articles:
        title = div.text
        link = ''
        in_quotes = False
        for char in str(div.a):
            if in_quotes and char == '"':
                in_quotes = False
            elif in_quotes:
                link += char
            elif char == '"':
                in_quotes = True
        link = 'greaterbinghamtonmls.com' + link
        title_link.append((title, link))
    return title_link
