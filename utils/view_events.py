
from utils.telegram_handlers import send_msg, edit_msg
from utils.firebase_handlers import retrieve_upcoming_events
from utils.data_validation import date_cleaner, time_cleaner
from utils.gcal_events import get_authenticated_service, delete_event_calendar


async def view_upcoming_events(db, session, chat_id, sent_message_id, edit=False):
    """To view all the upcoming events of the user"""
    try:
        result = retrieve_upcoming_events(db, chat_id)
        output_msg = None
        reply_markup = None
        
        # Formatting the events properly
        if result:
            output_msg = "<b><u>Upcoming events are</u></b>\n"
            for i in range(len(result)):
                formatted_date = result[i][1]
                formatted_message = (
                    f"\n{i+1}. <b>{result[i][0]}</b> on <i>{date_cleaner(formatted_date)}</i>"
                )
                output_msg += formatted_message

            # Adding inline buttons to view specific events
            reply_markup = {"inline_keyboard": [[]]}
            number = len(result)
            if number > 5:
                reply_markup["inline_keyboard"].append([])

            for i in range(number):
                if i <= 4:
                    reply_markup["inline_keyboard"][0].append(
                        {"text": i + 1, "callback_data": f"Button {i}"}
                    )
                if i >= 5:
                    reply_markup["inline_keyboard"][1].append(
                        {"text": i + 1, "callback_data": f"Button {i}"}
                    )
        else:
            output_msg = "<b>No upcoming events</b>\nPlease schedule events using TimeSked to view it here !"

        if edit:
            await edit_msg(session, chat_id, sent_message_id, output_msg, None, reply_markup, "HTML")
        else:
            await send_msg(session, chat_id, None, output_msg, reply_markup, "HTML")

    except Exception as e:
        print(f"An error has occurred in view_upcoming_events : {e}")


async def view_specific_event(db, session, chat_id, sent_message_id, button_number):
    """To view a specific event when an inline button is clicked"""
    try:
        result = retrieve_upcoming_events(db, chat_id)

        event_details = result[button_number]
        output_msg = "<b><u>Event Details</u></b>"
        output_msg += f"\n\n<b>Event name :</b> {event_details[0]}"
        output_msg += f"\n\n<b>Starting Date :</b> {date_cleaner(event_details[1])}"

        if event_details[2] is not None and event_details[2] != event_details[1]:
            output_msg += f"\n\n<b>Ending Date :</b> {date_cleaner(event_details[2])}"

        if event_details[3] is not None:
            output_msg += f"\n\n<b>Starting Time :</b> {time_cleaner(event_details[3])}"

        if event_details[4] is not None:
            output_msg += f"\n\n<b>Ending Time :</b> {time_cleaner(event_details[4])}"

        if event_details[5] is not None:
            output_msg += f"\n\n<b>Location :</b> {event_details[5]}"

        if event_details[6] is not None:
            output_msg += f"\n\n<b>Description :</b>\n{event_details[6]}"

        reply_markup = {
                "inline_keyboard": [
                    [
                        {
                            "text": "🔗 Event Link",
                            "url": event_details[7]
                        }
                    ],
                    [
                        {
                            "text": "🗑 Delete this event",
                            "callback_data": f"D3L%{event_details[8]}",
                        }
                    ],
                    [
                        {
                            "text": "<< Back to event list",
                            "callback_data": "Back to event_list",
                        }
                    ],
                ]
            }
        
        response = await edit_msg(session, chat_id, sent_message_id, output_msg, None, reply_markup, "HTML")

        if response.status_code != 200:
            print(f"Error sending message to Telegram: {response.text}")

    except Exception as e:
        print(f"An error has occurred in view_specific_event function {e}")


def delete_specific_event(db, chat_id, doc_id):
    try:
        event_id = None

        col_ref = db.collection("event_info")
        doc_ref = col_ref.document(doc_id)
        doc = doc_ref.get()
        if doc.exists:
            event_id = doc.to_dict()["event_id"]
        
        if event_id == "None":
            event_id = None

        if event_id:
            col_ref = db.collection("user_records")
            doc = col_ref.document(str(chat_id)).get().to_dict()
            calendar_id = doc["calendar_id"]
            access_token = doc["access_token"]
            refresh_token = doc["refresh_token"]
            
            service = get_authenticated_service(db, chat_id, access_token, refresh_token)
            delete_event_calendar(service, calendar_id, event_id)

        col_ref = db.collection("event_info")
        col_ref.document(str(doc_id)).delete()
        return True

    except Exception as e:
        print(f"An error occurred while deleting the specific event: {e}")
        return False