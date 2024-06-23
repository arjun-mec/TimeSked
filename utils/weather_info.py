import datetime
from urllib.parse import quote as url_quote

async def coordinates_retriever(session, location):
    """returns the coordinates, name and address of a given location"""
    try:
        location = location.lower()
        if "kochi" in location:
            location = location.replace("kochi", "ernakulam")

        encoded_location = url_quote(location)

        headers = {"User-Agent": "TimeSked v12 @Arjun_0o"}
        url = f"https://nominatim.openstreetmap.org/search?q={encoded_location}&format=json"
        response = await session.get(url, headers=headers)

        if response.status_code == 200:
            if response.json():
                data = response.json()[0]
                return {
                    "latitude": data["lat"],
                    "longitude": data["lon"],
                    "name": data["name"],
                    "address": data["display_name"],
                }

        else:
            print("Error:", response.status_code)

    except Exception as e:
        print(f"Error in coordinates_retriever {e}")


async def weather_retriever(session, coordinates, date_str, time_str, api_key):
    """Weather of a location is returned"""
    try:
        if coordinates:
            latitude = coordinates["latitude"]
            longitude = coordinates["longitude"]
            base_url = f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{latitude},{longitude}/{date_str}/{date_str}"

            params = {
                "key": api_key,
                "elements": "datetime,feelslike,precipprob,conditions",
                "unitGroup": "metric",
            }

            response = await session.get(base_url, params=params)

            if response.status_code == 200:
                try:
                    weather_data = response.json()

                    if time_str is not None:
                        time_obj = datetime.datetime.strptime(time_str, "%H:%M")
                        rounded_hour = time_obj.replace(
                            minute=0, second=0, microsecond=0
                        )
                        time = rounded_hour.strftime("%H:%M:%S")
                        for i in weather_data["days"][0]["hours"]:
                            if i["datetime"] == time:
                                return i

                    else:
                        day_weather = weather_data["days"][0]
                        day_weather.popitem()
                        return day_weather

                except Exception as e:
                    print(f"Couldnt retrieve weather info : {e}")

            else:
                print(f"Error in weather_retriever: {response.status_code}")

    except Exception as e:
        print(f"An error has occurred in weather_retriever : {e}")


def suggestion_giver(weather):
    """returns suggestions for the user's clothing based on the weather"""
    try:
        if weather:
            feels_like = weather["feelslike"]
            precipprob = weather["precipprob"]
            conditions = weather["conditions"]

            base_suggestion = (
                "It looks like the weather for your upcoming event will be "
            )

            # Base suggestion based on temperature
            if feels_like > 33:
                base_suggestion += "quite warm ☀️ . Opt for light and cool clothing."

            elif feels_like > 25:
                base_suggestion += "pleasant ✨ . Comfortable clothing is suitable."

            else:
                base_suggestion += (
                    "a bit cool ❄️ . It's a good idea to wear warmer clothing."
                )

            # Add conditions and precipitation probability considerations
            if precipprob > 40:
                suggestion = f"{base_suggestion} There's a {precipprob:.1f}% chance of rain ⛈️, so an umbrella is recommended ☔️."

            elif conditions == "Overcast":
                suggestion = f"{base_suggestion} The sky will be overcast ☁️. An umbrella might be helpful in case of unexpected rain ☂️."

            elif conditions in ("Clear", "Partially cloudy"):
                suggestion = base_suggestion

            else:
                suggestion = f"{base_suggestion} Adjust your attire accordingly to suit the {conditions.lower()} conditions."

            return suggestion

        else:
            return None

    except Exception as e:
        print(f"An error has occurred in suggestions_giver : {e}")
        return None