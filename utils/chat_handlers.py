from utils.telegram_handlers import send_msg, edit_msg, pin_msg, unpin_msg
from utils.data_validation import escape_markdownv2
from utils.firebase_handlers import retrieve_upcoming_events
from config import chat_model
import asyncio


async def search_handler(db, session, chat_id, confirm=False, sent_message_id=None):
    """Initiates the chat functionality for a user.

    If confirm is False, sends a confirmation message to the user to share
    their upcoming event details and clears the chat history upon session end.
    If confirm is True, retrieves user data, updates their status to "CHATTING",
    initializes chat history, and sends a welcome message.

    Args:
        db: Firestore client instance.
        session: httpx client session object.
        chat_id (int): Telegram chat ID of the user.
        confirm (bool, optional): Whether the user confirmed the chat initiation.
            Defaults to False.
        sent_message_id (int, optional): Message ID of the previously sent
            confirmation message (if any). Defaults to None.

    Raises:
        Exception: If an error occurs during the process, sends an error message
            to the user and prints the error message to the console.
    """
    try:
        if not confirm:
            text = "By clicking confirm, your 10 upcoming event details will be shared with Gemini. Your chat history will be cleared when this chat session is closed."
            reply_markup = {
                "inline_keyboard": [
                    [
                        {
                            "text": "⚠️ Confirm",
                            "callback_data": "Confirm CHAT",
                        }
                    ]
                ]
            }

            response = await send_msg(session, chat_id, None, text, reply_markup, None)

            sent_message_id = response.json()["result"]["message_id"]

        else:
            await edit_msg(
                session,
                chat_id,
                sent_message_id,
                "Getting chat mode ready! TimeSked will be right with you to talk about your events. 💬🗓️",
            )
            col_ref = db.collection("user_records")
            doc_ref = col_ref.document(str(chat_id))
            doc_ref.update({"position": "CHATTING"})

            chat_history_creator(db, chat_id, doc_ref)
            await edit_msg(
                session,
                chat_id,
                sent_message_id,
                "Chat mode is ready! 🎉 Ask TimeSked anything about your upcoming events. 💬🗓️",
            )
            response = await send_msg(
                session,
                chat_id,
                None,
                "📌 To exit chat mode, enter: /cancel",
            )
            sent_message_id = response.json()["result"]["message_id"]
            await pin_msg(session, chat_id, sent_message_id)

    except Exception as e:
        await send_msg(
            session,
            chat_id,
            None,
            "Hmm, encountering a slight glitch while setting up chat. ⚙️ Please try again in a bit",
        )
        print(f"Error in search_handler {e}")


def chat_history_creator(db, chat_id, doc_ref):
    """Creates and initializes the chat history for a user.

    Retrieves upcoming events from the database, formats them into a message,
    and updates the user's document in Firestore with the initial chat history.

    Args:
        db: Firestore client instance.
        chat_id (int): Telegram chat ID of the user.
        doc_ref: Firestore document reference of the user.

    Raises:
        Exception: If an error occurs during the process, prints the error
            message to the console.
    """
    try:
        result = retrieve_upcoming_events(db, chat_id)
        output = f"{result} This list contains the details about the upcoming events of the user."
        messages = [{"role": "user", "parts": [output]}]
        doc_ref.update({"chat_history": messages})

    except Exception as e:
        print(f"Error in chat_history_creator {e}")


async def chat_handler(
    db, session, chat_id, previous_messages, query_message, received_message_id
):
    """Handles user queries in the chat.

    Appends the user's message to the chat history, generates a response
    using the chat model, sends the response back to the user, and updates
    the chat history in Firestore.

    Args:
        db: Firestore client instance.
        session: httpx client session object.
        chat_id (int): Telegram chat ID of the user.
        previous_messages (list): List of previous messages in the chat.
        query_message (str): The user's query message.
        received_message_id (int): Message ID of the received user message.

    Raises:
        Exception: If an error occurs during the process, prints the error
            message to the console.
    """
    try:
        previous_messages.append(
            {
                "role": "user",
                "parts": [query_message],
            }
        )

        response = chat_model.generate_content(previous_messages)
        previous_messages.append({"role": "model", "parts": [response.text]})

        text = response.text
        output_text = escape_markdownv2(text)
        send_response = await send_msg(
            session, chat_id, received_message_id, output_text, parse_mode="MarkdownV2"
        )

        if not send_response:
            await send_msg(session, chat_id, received_message_id, text)

        asyncio.create_task(chat_history_updater(db, chat_id, previous_messages))

    except Exception as e:
        print(f"Error in chat_handler {e}")


async def chat_history_updater(db, chat_id, output):
    """Updates the chat history of a user in Firestore.

    Args:
        db: Firestore client instance.
        chat_id (int): Telegram chat ID of the user.
        output (list): Updated list of messages representing the chat history.

    Raises:
        Exception: If an error occurs during the process, prints the error
            message to the console.
    """
    try:
        col_ref = db.collection("user_records")
        doc_ref = col_ref.document(str(chat_id))
        doc_ref.update({"chat_history": output})
    except Exception as e:
        print(f"Error in chat_history_updater {e}")


def chat_history_retriever(db, chat_id):
    """Retrieves the chat history of a user from Firestore.

    Args:
        db: Firestore client instance.
        chat_id (int): Telegram chat ID of the user.

    Returns:
        list: List of messages representing the chat history, or None if
            an error occurs.
    """
    try:
        col_ref = db.collection("user_records")
        doc_ref = col_ref.document(str(chat_id)).get()
        return doc_ref.to_dict()["chat_history"]

    except Exception as e:
        print(f"Error in chat_history_retriever {e}")
        return None


def chat_history_deleter(db, chat_id):
    """Deletes the chat history of a user in Firestore.

    Sets the 'chat_history' and 'position' fields to None in the user's
    document.

    Args:
        db: Firestore client instance.
        chat_id (int): Telegram chat ID of the user.

    Raises:
        Exception: If an error occurs during the process, prints the error
            message to the console.
    """
    try:
        col_ref = db.collection("user_records")
        doc_ref = col_ref.document(str(chat_id))
        doc_ref.update({"chat_history": None, "position": None})

    except Exception as e:
        print(f"Error in chat_history_deleter {e}")


async def cancel_handler(db, session, chat_id):
    """Handles the /cancel command, ending the chat session.

    Deletes the user's chat history, sends a goodbye message,
    and unpins the exit chat message.

    Args:
        db: Firestore client instance.
        session: httpx client session object.
        chat_id (int): Telegram chat ID of the user.

    Raises:
        Exception: If an error occurs during the process, sends an error message
            to the user and prints the error message to the console.
    """
    try:
        chat_history_deleter(db, chat_id)
        await send_msg(
            session,
            chat_id,
            None,
            "See you later! Type /chat to start a new chat. 👍",
        )
        await unpin_msg(session, chat_id)

    except Exception as e:
        await send_msg(
            session,
            chat_id,
            None,
            "An error has occurred ! Please try again later.",
        )
        print(f"Error in cancel_handler {e}")
