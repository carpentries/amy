import airportsdata
from airportsdata import Airport
from django_countries import countries

FEE_DETAILS_URL = "https://carpentries.org/workshops/#workshop-cost"

STR_SHORT = 10  # length of short strings
STR_MED = 40  # length of medium strings
STR_LONG = 100  # length of long strings
STR_LONGEST = 255  # length of the longest strings
STR_REG_KEY = 20  # length of Eventbrite registration key

IATA_AIRPORTS = airportsdata.load("IATA")
COUNTRIES = dict(countries)


def airport_option_label(iata_code: str, airport: Airport) -> str:
    return f"{iata_code}: {airport['name']} ({COUNTRIES.get(airport['country'], '-')}, {airport['tz']})"
