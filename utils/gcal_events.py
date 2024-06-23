from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from config import return_flow

import datetime
from re import match
import asyncio


from utils.telegram_handlers import send_msg
from utils.firebase_handlers import event_info_add
from config import CAL_CLIENT_ID, CAL_CLIENT_SECRET


async def link_handler(session, chat_id, calendar_id):
    try:
        if not calendar_id:
            flow = return_flow()
            auth_url, _ = flow.authorization_url(
                access_type='offline',
                prompt='consent',
                state=str(chat_id),
            )

            auth_msg = "To add events seamlessly, TimeSked needs to connect with your Google Calendar. Click below to grant access! Don't worry, TimeSked can only create a dedicated calendar and add, view, or delete events within it. Your existing event details remain private. 👍"  
            reply_markup = {
                "inline_keyboard": [
                    [
                        {
                            "text": "🔗 Link",
                            "url": auth_url,
                            "callback_data": "Auth_Link"
                        }
                    ]
                ]
            }
            
            await send_msg(session, chat_id, None, auth_msg, reply_markup, None)

        else:
            output_msg = "No need to sign in again 😊 Your calendar is already registered with TimeSked, new events will be automatically added to your calendar!"


    except Exception as e:
        output_msg = "Authorisation failed, Please try again later" 
        await send_msg(session, chat_id, None, output_msg, None, None)
        print(f"Error in link_handler : {e}")


async def unlink_handler(db, session, chat_id, text=None, position=None):
    try:
        col_ref = db.collection("user_records")
        doc_ref = col_ref.document(str(chat_id))
        doc = doc_ref.get().to_dict()

        calendar_id = doc["calendar_id"]

        if not position:
            if calendar_id:
                doc_ref.update({"position": "DELETING"})
                warning_msg = "⚠️ Warning: Unlinking will permanently revoke TimeSked's access to your Google Calendar. TimeSked will no longer be able to create, view, or delete events on your behalf. This action cannot be reversed. 🤔 \n\nTo confirm deletion, please type 'CONFIRM'. Typing anything else will cancel the operation."
                await send_msg(session, chat_id, None, warning_msg)

            else:
                info_msg = "There are no calendars associated with your account at this time. If you add a calendar later, you can delete it here. 🗑️"
                await send_msg(session, chat_id, None, info_msg)

        else:
            if text == "CONFIRM":
                access_token = doc["access_token"]
                refresh_token = doc["refresh_token"]
                # delete_calendar(service, calendar_id) -- cannot delete calendar with this scope
                # unlink account -- remove access & refresh token
                await revoke_google_token(session, access_token)
                await revoke_google_token(session, refresh_token)

                info_msg = "👋 Okay, I've unlinked your Google Calendar from TimeSked. \nJust a heads-up: TimeSked does not have permission to delete calendars automatically. If you want to remove the TimeSked calendar completely, you can do that directly in your Google Calendar settings."
                await send_msg(session, chat_id, None, info_msg)

                doc_ref.update({"position": None, "calendar_id": None, "access_token": None, "refresh_token": None})

            else:
                info_msg = "🎉 The delete operation was canceled. Your calendar and events remain unchanged. "
                await send_msg(session, chat_id, None, info_msg)
                doc_ref.update({"position": None})

    except Exception as e:
        print(f"Error in unlink_handler {e}")

async def revoke_google_token(session, token):
    """Revokes a Google access or refresh token."""
    url = f'https://oauth2.googleapis.com/revoke?token={token}'

    response = await session.post(url)
    if response.status_code != 200:
        print(f"Error revoking token: {response.text}") 


async def first_signin(db, chat_id, access_token, refresh_token):
    col_ref = db.collection("user_records")
    doc_ref = col_ref.document(str(chat_id))
    doc = doc_ref.get().to_dict()
    calendar_id = doc["calendar_id"]
    if not calendar_id:
        service = get_authenticated_service(db, chat_id, access_token, refresh_token)
        calendar_id = create_calendar(service, "TimeSked")
        
    doc_ref.update({"access_token": access_token, "refresh_token": refresh_token, "calendar_id": calendar_id})

def get_authenticated_service(db, chat_id, access_token, refresh_token):

    credentials = Credentials(
        token = access_token,  
        refresh_token = refresh_token,
        token_uri = 'https://oauth2.googleapis.com/token', 
        client_id = CAL_CLIENT_ID, 
        client_secret = CAL_CLIENT_SECRET,
    )

    # Check if the token is expired
    if credentials.expired:
        credentials.refresh(Request())  # Refresh the token
        print("Access token refreshed!")  

        updated_access_token = credentials.token 

        col_ref = db.collection("user_records")
        doc_ref = col_ref.document(str(chat_id))
        doc_ref.update({"access_token": updated_access_token})

    service = build('calendar', 'v3', credentials=credentials)

    return service


def create_calendar(service, summary, time_zone="Asia/Kolkata"):
    try:
        calendar = {"summary": summary, "timeZone": time_zone}
        created_calendar = service.calendars().insert(body=calendar).execute()
        return created_calendar["id"]
    except Exception as e:
        print(f"Error creating calendar: {e}")
        return None 


async def add_event_to_calendar(service, calendar_id, event_details):
    (
        name,
        start_date,
        end_date,
        start_time,
        end_time,
        location,
        description,
    ) = event_details

    event = {
        "summary": name,
        "start": {
            "timeZone": "Asia/Kolkata",
        },
        "end": {
            "timeZone": "Asia/Kolkata",
        },
    }

    if start_time:
        start_datetime = f"{start_date}T{start_time}:00+05:30"
        event["start"]["dateTime"] = start_datetime

        if end_time:
            end_datetime = f"{end_date}T{end_time}:00+05:30"
            event["end"]["dateTime"] = end_datetime
        else:
            start_time_object = datetime.datetime.strptime(start_time, "%H:%M")
            end_time = start_time_object + datetime.timedelta(hours=1)
            end_time = end_time.strftime("%H:%M")
            end_datetime = f"{end_date}T{end_time}:00+05:30"
            event["end"]["dateTime"] = end_datetime
    else:
        event["start"]["date"] = start_date
        event["end"]["date"] = end_date

    if location:
        event["location"] = location
    if description:
        event["description"] = description

    event = service.events().insert(calendarId=calendar_id, body=event)
    return event


def delete_event_calendar(service, calendar_id, event_id):
    try:
        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
        print("Event deleted successfully.")
    except Exception as e:
        print(f"Error in delete event calendar {e}")


async def gcal_event_handler(db, waiting_msg, chat_id, received_message_id, sent_message_id, events, suggestions, calendar_id, queue):
    waiting_msg += "\n - Adding events to your calendar 🗓️"
    await queue.put((chat_id, sent_message_id, waiting_msg, received_message_id))

    list_of_events = []
    g_events = []

    col_ref = db.collection("user_records")
    doc_ref = col_ref.document(str(chat_id))
    doc = doc_ref.get().to_dict()

    access_token = doc["access_token"]
    refresh_token = doc["refresh_token"]

    service = get_authenticated_service(db, chat_id, access_token, refresh_token)
    for event_details in events:
        if isinstance(event_details, list):
            g_event = await add_event_to_calendar(
                service, calendar_id, event_details
            )
            g_events.append(g_event)
            list_of_events.append({"name": event_details[0], "start_date": event_details[1], "start_time": event_details[3], "location": event_details[5], "suggestions": suggestions})
        
        else:
            list_of_events.append(event_details)

    event_links_ids = batch_multiple_events(service, g_events)
    for idx, link_id in enumerate(event_links_ids):
        event_id = link_id["id"]
        list_of_events[idx].update({"link": link_id["link"]})
        asyncio.create_task(event_info_add(
            db,
            chat_id,
            received_message_id,
            events[idx],
            link_id["link"],
            event_id,
        ))
    
    return list_of_events


def batch_multiple_events(service, g_events):
    event_links_ids = []

    def callback(request_id, response, exception):
        if exception is not None:
            print(f"Error for request {request_id}: {exception}")
        else:
            event_links_ids.append({
                'id': response.get('id'),
                'link': response.get('htmlLink')
            })
    
    batch = service.new_batch_http_request(callback=callback)

    for g_event in g_events:
        batch.add(g_event)

    # Execute the batch request
    try:
        batch.execute()
    except HttpError as error:
        print(f"An error occurred in batch_multiple_events : {error}")
    
    return event_links_ids