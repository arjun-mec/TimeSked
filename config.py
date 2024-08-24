import os
import google.generativeai as genai
import datetime
from google_auth_oauthlib.flow import Flow
import json

# from dotenv import load_dotenv

# load_dotenv()


def return_flow():
    try:
        creds_info = os.environ.get("GCAL_CRED")
        creds_json = json.loads(creds_info)
        REDIRECT_URI = "https://timesked.koyeb.app/oauthcallback"
        flow = Flow.from_client_config(
            creds_json,
            scopes=["https://www.googleapis.com/auth/calendar.app.created"],
            redirect_uri=REDIRECT_URI,
        )

        return flow
    except Exception as e:
        print(f"Could not return flow : {e}")


TOKEN = os.environ.get("TIMESKED_TOKEN")
FIREBASE_TOKEN = os.environ.get("FIREBASE")
weather_api_key = os.environ.get("WEATHER_API_KEY")

CAL_CLIENT_ID = os.environ.get("CAL_CLIENT_ID")
CAL_CLIENT_SECRET = os.environ.get("CAL_CLIENT_SECRET")

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

generation_config = {
    "temperature": 0.4,
    "response_mime_type": "application/json",
}

text_model = genai.GenerativeModel(
    model_name="gemini-1.5-flash-latest",
    generation_config=generation_config,
    system_instruction="All the details must strictly be from the context of the message. You can be creative within the details mentioned, but do not add information yourself. NEVER CREATE ANY EVENTS THAT ISNT PRESENT IN THE DATA GIVEN TO YOU. If the message does not contain details about any events and isnt related to events, then respond with an empty list [], else in all cases the output should be a nested list and each nested list must always contain 7 elements. An event can be considered valid only if it has both an event name and a starting date, if not then you should respond with an empty list.",
)

img_model = genai.GenerativeModel(
    model_name="gemini-1.5-flash-latest",
    generation_config=generation_config,
    system_instruction="All the details must strictly be from the context of the message. You can be creative within the details mentioned, but do not add information yourself. NEVER CREATE ANY EVENTS THAT ISNT PRESENT IN THE DATA GIVEN TO YOU. If the message does not contain details about any events and isnt related to events, then respond with an empty list [], else in all cases the output should be a nested list and each nested list must always contain 7 elements. An event can be considered valid only if it has both an event name and a starting date, if not then you should respond with an empty list.",
)

chat_model = genai.GenerativeModel(
    model_name="gemini-1.5-flash-latest",
    generation_config={"temperature": 0.5},
    system_instruction="You are a Telegram chatbot. Your purpose is to assist users with their upcoming events. You will be provided with event details, the link provided in the link section is the google calendar event link and the link that might be present in the description is the registration link. Respond to user queries based strictly on the provided information. Avoid answering questions unrelated to these events or making assumptions not explicitly stated in the data. You are allowed to format your output such that it is more readable to the user such as converting dates to dd-month-year format and time to 12 hour format. Strictly follow MarkdownV2 Telegram API friendly formatting to make it more readable. All entities opened must be closed properly. If the user asks on how to exit chat mode, ask the user to send the /cancel command.",
)


today = datetime.date.today()
date_today = today.strftime("%Y-%m-%d")
day_today = today.strftime("%A")

query = f"""
I need you to act as an professional event extractor. I will provide you with text or an image that describes one or more events, and you will extract the relevant details and format them into a nested list. 
Each inner list should represent one event and contain the following information in this order:

* The name of the event.
* The start date of the event in YYYY-MM-DD format. 
* The end date of the event in YYYY-MM-DD format. 
* The start time of the event in 24-hour format (e.g., 14:00).
* The end time of the event in 24-hour format (e.g., 15:00).
* The location of the event.
* A brief description of the event (maximum 50 words). Include registration links and fees if mentioned. 

If any of these details are not available in the provided text, use "None" as a placeholder.

**Date Handling:**

* If a specific start date is mentioned, use that. Make sure it's in the YYYY-MM-DD format, and convert it if necessary.
* If a day of the week is mentioned (e.g., Monday), provide the date of the next occurrence, considering today's date is {date_today} and today's day is {day_today}.
* Event deadline/Last Date/Due Date/Submission Date all can be considered as the start date if no other starting date is mentioned. If the message says apply before this date, then consider that date as the starting date if there are no other starting date mentioned.
* If a date is in an invalid format (any format that is not a standard human-readable date like YYYY-MM-DD or DD/MM/YYYY), you MUST use 'None'. Do not attempt to interpret or correct invalid dates. For example, if the date in the message says 25/40/2024, you should realise that it is a invalid date and respond with "None" as the date.
* If no date is mentioned, use "None".

**Time Formatting:**

* Use 24-hour format for time (e.g., 19:00 for 7 PM or 09:30 for 9:30 AM).
* If AM/PM format is used, convert it to 24-hour format.
* If only the hour is mentioned, assume the event starts at the beginning of that hour (e.g., 14:00 for 2 PM).

**Location:**

* Prioritize the college name if present. 
* If the college name is unavailable or ambiguous, use the most specific location information available. 
* If no location information is provided, use "None".

If the message is not about any event and is not related to any events, then you should respond with an empty list []. Never generate example events.
There is chance for either a single event being present in the message or multiple, make sure to act accordingly. An event can be considered valid only if it contains an event name and a starting date.
Strictly adhere to nested array format and follow the rules specified above. EVERY NESTED LIST SHOULD ALWAYS HAVE 7 elements unless if the message isnt about events, then respond with []. Do not do any formatting on the array, your output must be a valid python list. Try your best to extract event information from the message/image.
"""
