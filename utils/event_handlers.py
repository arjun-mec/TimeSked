from utils.telegram_handlers import (
    send_msg,
    send_typing_action,
    edit_msg,
    final_edit_msg,
    image_downloader,
    send_location_action,
    send_venue,
)
import asyncio
from utils.firebase_handlers import new_msg_updater, event_info_add
from utils.data_validation import process_events, date_cleaner, escape_markdownv2
from utils.gemini_models import prompter
from utils.weather_info import (
    coordinates_retriever,
    weather_retriever,
    suggestion_giver,
)
from utils.gcal_events import gcal_event_handler
from utils.view_events import (
    view_specific_event,
    view_upcoming_events,
    delete_specific_event,
)
from utils.chat_handlers import search_handler
from utils.gcal_events import get_authenticated_service, delete_event_calendar
from google.cloud.firestore_v1.base_query import FieldFilter
import traceback
from config import weather_api_key, TOKEN
import datetime
from urllib.parse import quote as url_quote
import traceback


async def text_logic(db, session, msg, chat_id, received_message_id, queue):
    """Handles logic for incoming text messages.

    Extracts text from the message, sends a waiting message, triggers event
    detail extraction, updates the database with the new message, and handles
    potential errors.

    Args:
        db: Firestore client instance.
        session: httpx asynchronous client session object.
        msg (dict): Telegram message data.
        chat_id (int): Telegram chat ID of the user.
        received_message_id (int): Message ID of the received user message.
        queue (asyncio.Queue): Queue for managing asynchronous operations.

    Raises:
        Exception: If an error occurs during the process, sends an error message
            to the user and prints the error message to the console.
    """
    try:
        txt = msg["message"]["text"]
        waiting_msg = "⏳ Please Wait while TimeSked does its job... "
        response = await send_msg(
            session,
            chat_id,
            received_message_id,
            waiting_msg,
        )
        asyncio.create_task(send_typing_action(session, chat_id))
        sent_message_id = response.json()["result"]["message_id"]

        await text_img_handler(
            db,
            session,
            "text",
            chat_id,
            sent_message_id,
            received_message_id,
            txt,
            queue,
        )

        asyncio.create_task(new_msg_updater(db, chat_id, received_message_id, txt))

    except Exception as e:
        await queue.join()
        output_msg = "An error has occurred in text logic. Please try again later"
        print(output_msg + f"\n {e}")
        await final_edit_msg(
            session,
            chat_id,
            sent_message_id,
            output_msg,
            received_message_id,
        )


async def photo_logic(db, session, msg, chat_id, received_message_id, queue):
    """Handles logic for incoming photo messages.

    Downloads the photo, sends a waiting message, triggers event detail
    extraction, updates the database with the new message and file ID, and
    handles potential errors.

    Args:
        db: Firestore client instance.
        session: httpx asynchronous client session object.
        msg (dict): Telegram message data.
        chat_id (int): Telegram chat ID of the user.
        received_message_id (int): Message ID of the received user message.
        queue (asyncio.Queue): Queue for managing asynchronous operations.

    Raises:
        Exception: If an error occurs during the process, sends an error message
            to the user and prints the error message to the console.
    """
    image = None
    try:
        waiting_msg = "⏳ Please Wait while TimeSked does its job... \nThis might take upto 10 seconds !⏳"
        response = await send_msg(
            session,
            chat_id,
            received_message_id,
            waiting_msg,
        )
        sent_message_id = response.json()["result"]["message_id"]
        asyncio.create_task(send_typing_action(session, chat_id))

        file_id = msg["message"]["photo"][-2]["file_id"]
        image = await image_downloader(session, file_id)

    except Exception as e:
        await queue.join()
        print(f"Downloading Photo failed ! {e}")
        traceback.print_exc()
        await final_edit_msg(
            session,
            chat_id,
            sent_message_id,
            "Opening the photo failed, Please send it again",
            received_message_id,
        )

    if image:
        waiting_msg += " \n\n - Image Downloaded ✨"
        await queue.put((chat_id, sent_message_id, waiting_msg, received_message_id))
        try:
            asyncio.create_task(send_typing_action(session, chat_id))
            await text_img_handler(
                db,
                session,
                "image",
                chat_id,
                sent_message_id,
                received_message_id,
                image,
                queue,
            )
            db_file_id = "F!L3" + str(file_id)
            asyncio.create_task(
                new_msg_updater(db, chat_id, received_message_id, db_file_id)
            )

        except Exception as e:
            await queue.join()
            output_msg = "An error has occurred in photo logic. Please try again later"
            print(output_msg + f"\n{e}")
            await final_edit_msg(
                session,
                chat_id,
                sent_message_id,
                output_msg,
                received_message_id,
            )


async def text_img_handler(
    db, session, type, chat_id, sent_message_id, received_message_id, message, queue
):
    """Handles event extraction, processing, and calendar interaction for text and image messages.

    Processes the extracted events, retrieves calendar ID, handles both Google Calendar
    and link-based event creation, and constructs the final message with event details.

    Args:
        db: Firestore client instance.
        session: httpx asynchronous client session object.
        type (str): Type of message, either "text" or "image".
        chat_id (int): Telegram chat ID of the user.
        sent_message_id (int): Message ID of the sent message to be updated.
        received_message_id (int): Message ID of the received user message.
        message (str or bytes): Text content or image data.
        queue (asyncio.Queue): Queue for managing asynchronous operations.

    Raises:
        Exception: If an error occurs during the process, sends an error message
            to the user and prints the error message to the console.
    """
    try:
        retries = 3
        for attempt in range(retries):
            unprocessed_events = None
            # send the corresponding message
            if type == "text":
                waiting_msg = "⏳ Please Wait while TimeSked does its job... \nThis might take upto 10 seconds !⏳\n\n - Extracting event details 🔍"
            else:
                waiting_msg = "⏳ Please Wait while TimeSked does its job... \nThis might take upto 10 seconds !⏳\n\n - Image downloaded successfully ✨\n - Extracting event details 🔍"

            await queue.put(
                (chat_id, sent_message_id, waiting_msg, received_message_id)
            )
            asyncio.create_task(send_typing_action(session, chat_id))

            # prompt the model
            unprocessed_events = prompter(type, message)

            if isinstance(unprocessed_events, list):
                break
            else:
                output_msg = f"Attempt {attempt + 1} failed ❌. \nReattempting, Please Wait... ⌛"
                await queue.put(
                    (chat_id, sent_message_id, output_msg, received_message_id)
                )
                asyncio.create_task(send_typing_action(session, chat_id))
                retries -= 1

        else:
            await queue.join()

            if "internal error" in unprocessed_events:
                output_msg = "Gemini is currently experiencing a temporary hiccup. Please try again in a little while."
            else:
                output_msg = "All attempts to extract event details failed, sorry for the incovenience caused. Please try again later"

            await final_edit_msg(
                session,
                chat_id,
                sent_message_id,
                output_msg,
                received_message_id,
            )
            return None

        waiting_msg += "\n - Event detail extraction successful 🎉"
        await queue.put((chat_id, sent_message_id, waiting_msg, received_message_id))
        asyncio.create_task(send_typing_action(session, chat_id))

        events = process_events(unprocessed_events)

        # sent the appropriate message if model response is []
        if events == [] or events == [[]]:
            output_msg = "Oops! Looks like that message is missing some key event details. Please try again, and I'll get it added to your calendar. 🗓️"
            await queue.join()
            await final_edit_msg(
                session, chat_id, sent_message_id, output_msg, received_message_id
            )
            return None

        suggestions = None
        coordinates = None
        if len(events) == 1:
            if isinstance(events[0], ValueError):
                output_msg = (
                    str(events[0])
                    + "📅 Please check your input and try again.\n\nIf you feel this is incorrect, Please click on the 'Regenerate' button given below 👇."
                )
                await queue.join()
                await final_edit_msg(
                    session,
                    chat_id,
                    sent_message_id,
                    output_msg,
                    received_message_id,
                )
                return None

            # weather suggestions for single event
            location = events[0][5]
            if location is not None:
                coordinates = await coordinates_retriever(session, location)
                weather = await weather_retriever(
                    session,
                    coordinates,
                    events[0][1],
                    events[0][3],
                    weather_api_key,
                )
                suggestions = suggestion_giver(weather)

        # retrives calendar id of that user (if present)
        col_ref = db.collection("user_records")
        doc = col_ref.document(str(chat_id)).get()
        calendar_id = doc.to_dict()["calendar_id"]

        if calendar_id:
            flag = "gcal"
            list_of_events = await gcal_event_handler(
                db,
                waiting_msg,
                chat_id,
                received_message_id,
                sent_message_id,
                events,
                suggestions,
                calendar_id,
                queue,
            )

        else:
            flag = "link"
            list_of_events = await link_event_handler(
                db,
                waiting_msg,
                chat_id,
                received_message_id,
                sent_message_id,
                events,
                suggestions,
                queue,
            )

        print(f"\nProcessed events : \n{list_of_events}")
        await message_creator(
            session,
            list_of_events,
            chat_id,
            sent_message_id,
            received_message_id,
            flag,
            coordinates,
            queue,
        )

    except Exception as e:
        error_msg = f"Sorry ! An error has occurred \n{e}"
        await queue.put((chat_id, sent_message_id, error_msg, received_message_id))
        print("Error in text_img_handler \n", e)


async def link_event_handler(
    db,
    waiting_msg,
    chat_id,
    received_message_id,
    sent_message_id,
    events,
    suggestions,
    queue,
):
    """Handles the creation and storage of pre-filled Google Calendar event links.

    Processes each event, generates a shortened Google Calendar link, updates the database
    with event information, and manages the asynchronous operations through the queue.

    Args:
        db: Firestore client instance.
        waiting_msg (str): Waiting message to be sent to the user.
        chat_id (int): Telegram chat ID of the user.
        received_message_id (int): Message ID of the received user message.
        sent_message_id (int): Message ID of the sent message to be updated.
        events (list): List of processed events.
        suggestions (str, optional): Weather-based suggestions for the event.
                                     Defaults to None.
        queue (asyncio.Queue): Queue for managing asynchronous operations.

    Returns:
        list: List of dictionaries, each containing event details and the generated link.
    """
    waiting_msg += "\n - Link generation in process 🔗"
    await queue.put((chat_id, sent_message_id, waiting_msg, received_message_id))

    list_of_events = []
    for event_details in events:
        if isinstance(event_details, list):
            short_link = categorize(event_details)
            list_of_events.append(
                {
                    "name": event_details[0],
                    "start_date": event_details[1],
                    "start_time": event_details[3],
                    "location": event_details[5],
                    "link": short_link,
                    "suggestions": suggestions,
                }
            )
            asyncio.create_task(
                event_info_add(
                    db, chat_id, received_message_id, event_details, short_link
                )
            )
        else:
            list_of_events.append(event_details)

    return list_of_events


async def message_creator(
    session,
    events,
    chat_id,
    sent_message_id,
    received_message_id,
    type,
    coordinates,
    queue,
):
    """Creates and sends the final message with event details and links.

    Constructs a message based on the type of event handling (Google Calendar or link-based),
    formats the message with event information, and sends the final response to the user.

    Args:
        session: httpx asynchronous client session object.
        events (list): List of event details, including name, date, time, location, and link.
        chat_id (int): Telegram chat ID of the user.
        sent_message_id (int): Message ID of the sent message to be updated.
        received_message_id (int): Message ID of the received user message.
        type (str):  Type of event handling, either "gcal" or "link".
        coordinates (tuple, optional): Latitude and longitude coordinates of the event location.
                                       Defaults to None.
        queue (asyncio.Queue): Queue for managing asynchronous operations.
    """
    multiple_events = True

    if type == "gcal":
        if len(events) == 1:
            multiple_events = False
            event_details = events[0]
            if event_details["suggestions"]:
                events_message = f"🎉 Your event has been added to your calendar\\! \n\n\t🗓️ Event\\: {escape_markdownv2(event_details['name'])} \n\n\t📅 Date\\: {escape_markdownv2(date_cleaner(event_details['start_date']))} \n\n\t📍 Location\\: {escape_markdownv2(event_details['location'])} \n\n\t🔗 Event Link\\: [Event Link]({event_details['link']}) \n\n{escape_markdownv2(event_details['suggestions'])} \n\nEnjoy your event\\!"
            else:
                events_message = f"🎉 Your event has been added to your calendar\\! \n\n\t🗓️ Event\\: {escape_markdownv2(event_details['name'])} \n\n\t📅 Date\\: {escape_markdownv2(date_cleaner(event_details['start_date']))} \n\n\t🔗 Event Link\\: [Event Link]({event_details['link']}) \n\nEnjoy your event\\!"
        else:
            events_message = "🎉 Here are the details to your events ✨ \nAll the valid events have been added to your calendar\\! \n"

    else:
        if len(events) == 1:
            multiple_events = False
            event_details = events[0]
            if event_details["suggestions"]:
                events_message = f"Here's the pre\\-filled link to your 📅 calendar event\\: ✨\n\n\t🗓️ Event\\: {escape_markdownv2(event_details['name'])} \n\n\t📅 Date\\: {escape_markdownv2(date_cleaner(event_details['start_date']))} \n\n\t📍 Location\\: {escape_markdownv2(event_details['location'])} \n\n\t🔗 Event Link\\: [Event Link]({event_details['link']}) \n\n{escape_markdownv2(event_details['suggestions'])} \n\nEnjoy your event\\!"
            else:  # no suggestion
                events_message = f"Here's the pre\\-filled link to your 📅 calendar event\\: ✨\n\n\t🗓️ Event\\: {escape_markdownv2(event_details['name'])} \n\n\t📅 Date\\: {escape_markdownv2(date_cleaner(event_details['start_date']))} \n\n\t🔗 Event Link\\: [Event Link]({event_details['link']}) \n\nEnjoy your event\\!"
        else:
            events_message = "Here's the details to your 📅 calendar events\\: \nClick on the link to add it to your calendar \n"

    if multiple_events:
        i = 1
        for event_details in events:
            if isinstance(event_details, ValueError):
                events_message += (
                    f"\n📅 Event \\#{i}\n{escape_markdownv2(str(event_details))}\n"
                )
            else:
                if not event_details["start_time"]:
                    event_details["start_time"] = ""
                events_message += f"\n📅 Event \\#{i} \n{escape_markdownv2(event_details['name'])} \n{escape_markdownv2(date_cleaner(event_details['start_date']))}  {escape_markdownv2(event_details['start_time'])} \nLocation \\: {escape_markdownv2(event_details['location'])} \nLink \\: [Event Link]({event_details['link']})\n"

            i += 1

    # events_message = escape_markdownv2(events_message)

    await queue.join()
    if len(events) == 1:
        await final_edit_msg(
            session,
            chat_id,
            sent_message_id,
            events_message,
            received_message_id,
            events[0]["location"],
            coordinates,
            parse_mode="MarkdownV2",
        )
    else:
        await final_edit_msg(
            session,
            chat_id,
            sent_message_id,
            events_message,
            received_message_id,
            None,
            None,
            parse_mode="MarkdownV2",
        )


def categorize(event_details):
    """Categorizes and generates a Google Calendar event link from provided event details.

    Processes event details, formats dates and times, constructs the Google Calendar link with
    encoded parameters, and returns the generated link.

    Args:
        event_details (list): List containing event name, start date, end date, start time,
                              end time, location, and description.

    Returns:
        str: The generated Google Calendar event link. If an error occurs, returns an error
             message string.
    """
    try:
        if isinstance(event_details, list):  # if event_details is a list
            name, start_date, end_date, start_time, end_time, location, description = (
                event_details
            )
            # Format event dates
            event_start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
            event_end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d")
            formatted_start_date = event_start_date.strftime("%Y%m%d")
            formatted_end_date = event_end_date.strftime("%Y%m%d")

            # Format start time
            formatted_start_time = None
            if start_time is not None:
                start_datetime = datetime.datetime.strptime(start_time, "%H:%M")
                formatted_start_time = start_datetime.strftime("%H%M%S")

            # Format end time
            formatted_end_time = None
            if end_time is not None:
                end_datetime = datetime.datetime.strptime(end_time, "%H:%M")
                formatted_end_time = end_datetime.strftime("%H%M%S")

            # setting the datetime param
            if formatted_start_time:
                if not formatted_end_time:
                    end_datetime = start_datetime + datetime.timedelta(hours=1)
                    formatted_end_time = end_datetime.strftime("%H%M%S")
                datetime_param = f"{formatted_start_date}T{formatted_start_time}/{formatted_end_date}T{formatted_end_time}"
            else:
                if formatted_end_date:
                    end_date = event_end_date + datetime.timedelta(days=1)
                    datetime_param = (
                        f"{formatted_start_date}/{end_date.strftime('%Y%m%d')}"
                    )
                else:
                    end_date = event_start_date + datetime.timedelta(days=1)
                    datetime_param = (
                        f"{formatted_start_date}/{end_date.strftime('%Y%m%d')}"
                    )

            # Encoding parameters
            encoded_event_name = url_quote(name)
            encoded_datetime_param = url_quote(datetime_param)

            # Construct link
            link_components = [
                f"text={encoded_event_name}",
                f"dates={encoded_datetime_param}",
            ]

            if location is not None:
                encoded_location = url_quote(location)
                link_components.append(f"location={encoded_location}")

            if description is not None:
                encoded_description = url_quote(description)
                link_components.append(f"details={encoded_description}")

            link = f"https://www.google.com/calendar/render?action=TEMPLATE&{'&'.join(link_components)}"

            # Return calendar event link
            return link
        else:
            print(event_details)
            return event_details

    except Exception as e:
        print(f"An error has occurred in the categorize function {e}")
        return "❌ An error has occurred. Please try again later"


async def handle_callback_query(db, session, callback_query, queue):
    """Handles all callback queries from inline keyboard buttons.

    Manages various callback actions, including event regeneration, location sharing,
    viewing and deleting specific events, and navigating between event lists.

    Args:
        db: Firestore client instance.
        session: httpx asynchronous client session object.
        callback_query (dict): Telegram callback query data.
        queue (asyncio.Queue): Queue for managing asynchronous operations.

    Raises:
        Exception: If an error occurs during event regeneration, restores the previous
            bot response and prints the error message to the console. Prints any other
            errors encountered to the console.
    """
    try:
        chat_id = callback_query["message"]["chat"]["id"]
        sent_message_id = callback_query["message"]["message_id"]

        if callback_query["data"].startswith("RE^!"):
            received_message_id = int(callback_query["data"][4:])
            await queue.put(
                (
                    chat_id,
                    sent_message_id,
                    "Working on it! Deleting those previous events... This might take a moment. ⏳",
                    received_message_id,
                )
            )
            regen_deleter(db, chat_id, received_message_id)

            tg_response = callback_query["message"]["reply_to_message"]
            if "photo" in tg_response:
                file_id = tg_response["photo"][-2]["file_id"]
                message = await image_downloader(session, file_id)
                await text_img_handler(
                    db,
                    session,
                    "Image",
                    chat_id,
                    sent_message_id,
                    received_message_id,
                    message,
                    queue,
                )
            else:
                message = tg_response["text"]
                await text_img_handler(
                    db,
                    session,
                    "text",
                    chat_id,
                    sent_message_id,
                    received_message_id,
                    message,
                    queue,
                )

        elif callback_query["data"].startswith("L0C@"):
            asyncio.create_task(send_location_action(session, chat_id))
            await send_venue(session, chat_id, callback_query["data"][4:])

            url = f"https://api.telegram.org/bot{TOKEN}/answerCallbackQuery"
            data = {"callback_query_id": callback_query["id"]}
            await session.post(url, json=data)

        elif callback_query["data"].startswith("Button"):
            button_number = int(callback_query["data"][6:])
            await view_specific_event(
                db, session, chat_id, sent_message_id, button_number
            )

            url = f"https://api.telegram.org/bot{TOKEN}/answerCallbackQuery"
            data = {"callback_query_id": callback_query["id"]}
            await session.post(url, json=data)

        elif callback_query["data"].startswith("D3L%"):
            doc_id = callback_query["data"][4:]
            delete_flag = delete_specific_event(db, chat_id, doc_id)

            if delete_flag:
                url = f"https://api.telegram.org/bot{TOKEN}/answerCallbackQuery"
                data = {
                    "callback_query_id": callback_query["id"],
                    "text": "Event deleted! ✅",
                    "show_alert": True,
                }
                await session.post(url, json=data)
                await view_upcoming_events(
                    db, session, chat_id, sent_message_id, edit=True
                )

        elif callback_query["data"] == "Back to event_list":
            await view_upcoming_events(db, session, chat_id, sent_message_id, edit=True)
            url = f"https://api.telegram.org/bot{TOKEN}/answerCallbackQuery"
            data = {"callback_query_id": callback_query["id"]}
            await session.post(url, json=data)

        elif callback_query["data"] == "Confirm CHAT":
            await search_handler(db, session, chat_id, True, sent_message_id)
            url = f"https://api.telegram.org/bot{TOKEN}/answerCallbackQuery"
            data = {"callback_query_id": callback_query["id"]}
            await session.post(url, json=data)

    except Exception as e:
        if callback_query["data"].startswith("RE^!"):
            received_message_id = int(callback_query["data"][4:])

            bot_prev_response = ""
            if "an error occurred" not in callback_query["message"]["text"]:
                bot_prev_response = "An error occurred while regenerating. TimeSked's previous response has been restored \n\n"

            bot_prev_response += callback_query["message"]["text"]

            await queue.join()
            await final_edit_msg(
                session,
                chat_id,
                sent_message_id,
                bot_prev_response,
                received_message_id,
            )
        print(f"An error has occurred in handle_callback_query function \n {e}")
        traceback.print_exc()


def regen_deleter(db, chat_id, message_id):
    """Deletes events from both Google Calendar and Firestore related to a specific message.

    Retrieves event IDs and document IDs from Firestore, deletes the documents,
    authenticates with Google Calendar API, and deletes the corresponding events.

    Args:
        db: Firestore client instance.
        chat_id (int): Telegram chat ID of the user.
        message_id (int): Message ID associated with the events to be deleted.
    """
    col_ref = db.collection("event_info")
    # gets the event ids and doc ids of the events to be deleted from calendar and documents respectively
    events_ids = []
    doc_ids = []

    docs = col_ref.where(filter=FieldFilter("message_id", "==", message_id)).get()
    for doc in docs:
        events_ids.append(doc.to_dict()["event_id"])
        doc_ids.append(doc.id)

    # deleting docs from firebase
    for doc_id in doc_ids:
        col_ref.document(str(doc_id)).delete()

    if len(events_ids) > 0:
        if events_ids[0]:
            # deleting events from calendar
            col_ref = db.collection("user_records")
            doc = col_ref.document(str(chat_id)).get().to_dict()
            calendar_id = doc["calendar_id"]
            access_token = doc["access_token"]
            refresh_token = doc["refresh_token"]
            service = get_authenticated_service(
                db, chat_id, access_token, refresh_token
            )
            for event_id in events_ids:
                delete_event_calendar(service, calendar_id, event_id)


async def start_handler(session, msg, chat_id, received_message_id):
    """Handles the /start command, sending a welcome message to the user.

    Args:
        session: httpx asynchronous client session object.
        msg (dict): Telegram message data.
        chat_id (int): Telegram chat ID of the user.
        received_message_id (int): Message ID of the received user message.

    Raises:
        Exception: If an error occurs during the process, sends an error message
            to the user and prints the error message to the console.
    """
    try:
        username = msg["message"]["from"].get("first_name")
        if not username:
            username = ""

        welcome_text = f"Heyy {username} ! Welcome to TimeSked 💫 \nTo start scheduling events in your calendar, simply send an event message 😊 \n\n💡Tip: Connect to your Google Calendar to let TimeSked automatically schedule events for you. /linkcalendar 👈 Tap here to link your calendar!"

        await send_msg(session, chat_id, None, welcome_text)

    except Exception as e:
        error_msg = "❌ An error has occurred. Please try again later, Sorry for the inconvenience"
        await send_msg(session, chat_id, received_message_id, error_msg)
        print(f"An error has occurred in start_handler : {e}")
