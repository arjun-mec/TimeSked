import datetime
from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter


today = datetime.date.today()
date_today = today.strftime("%Y-%m-%d")


def user_handler(db, msg):
    col_ref = db.collection("user_records")
    try:
        # Extract user information
        chat_id = msg["message"]["from"]["id"]
        first_name = msg["message"]["from"].get("first_name")
        last_name = msg["message"]["from"].get("last_name")
        username = msg["message"]["from"].get("username")
        date = datetime.date.today().strftime("%d-%m-%y")

        # Construct user name
        name = f"{first_name} {last_name}" if first_name and last_name else first_name or last_name or "Not Available" 

        doc_ref = col_ref.document(str(chat_id))
        doc = doc_ref.get()
        
        # Insert new user or update existing record
        if doc.exists:
            doc_ref.update({"no_of_uses":firestore.Increment(1)})
        else:
            doc_ref.set({"chat_id":chat_id, "name":name, "username":username, "date":date, "no_of_uses":1})

    except Exception as e:
        print(f"An error occurred in user_handler function : {e}")


async def new_msg_updater(db, chat_id, message_id, message_text):
    """Upong receiving a new message, the message text is added to the database"""
    col_ref = db.collection("message_log")
    try:
        doc_ref = col_ref.document(str(message_id))
        doc_ref.set({"chat_id": chat_id, "message_id": message_id, "message_text": message_text, "date": date_today})
    except Exception as e:
        print(f"An error occurred while updating message: {e}")


async def event_info_add(db, chat_id, message_id, event_details, link, event_id=None):
    """When a new event is created, the event details are added to the database"""
    col_ref = db.collection("event_info")
    try:
        (
            name,
            start_date,
            end_date,
            start_time,
            end_time,
            location,
            description,
        ) = event_details

        if start_time is not None:
            formatted_start_time = (
                datetime.datetime.strptime(start_time, "%H:%M")
                .replace(second=0)
                .strftime("%H:%M:%S")
            )
        else:
            formatted_start_time = None

        if end_time is not None:
            formatted_end_time = (
                datetime.datetime.strptime(end_time, "%H:%M")
                .replace(second=0)
                .strftime("%H:%M:%S")
            )
        else:
            formatted_end_time = None
        
        col_ref.add({"chat_id": chat_id, "message_id": message_id, "name": name, "start_date": start_date, "end_date": end_date, "start_time": formatted_start_time, "end_time": formatted_end_time, "location": location, "description": description, "link": link, "event_id": event_id})

    except Exception as e:
        print(f"An error occurred while adding event info : {e}")


def retrieve_upcoming_events(db, chat_id):
    col_ref = db.collection("event_info")
    try:
        docs = col_ref.where(filter=FieldFilter("chat_id", "==", chat_id)).where(filter=FieldFilter("start_date", ">=", date_today)).order_by("start_date").limit(10).get()
        result = []
        for doc in docs:
            doc_id = doc.id
            doc = doc.to_dict()
            event = [doc["name"], doc["start_date"], doc["end_date"], doc["start_time"], doc["end_time"], doc["location"], doc["description"], doc["link"], doc_id]
            result.append(event)

        if result:
            return result

    except Exception as e:
        print(f"An error occurred while retrieving message: {e}")
        return "An error occurred. Please try again later."


def dashboard_data(db):
    try:
        user_ref = db.collection("user_records")
        msg_ref = db.collection("message_log")
        event_ref = db.collection("event_info")

        user_count = user_ref.count().get()[0][0].value
        msg_count = msg_ref.count().get()[0][0].value + 210
        event_count = event_ref.count().get()[0][0].value + 154

        results = [user_count, msg_count, event_count]

        return results

    except Exception as e:
        print(f"Could not retrieve values {e}")
        return ["None", "None", "None"]