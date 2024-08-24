# TimeSked V13 - Proper OAuth flow for signing in

from fastapi import FastAPI, Response
from fastapi import Request as fast_request, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from firebase_admin import initialize_app
from firebase_admin import credentials
from firebase_admin import firestore
import json

from utils.firebase_handlers import dashboard_data, user_handler
from utils.telegram_handlers import (
    send_msg,
    edit_msg,
    final_edit_msg,
    send_typing_action,
)
from utils.event_handlers import (
    text_logic,
    photo_logic,
    start_handler,
    handle_callback_query,
)
from utils.view_events import view_upcoming_events
from utils.chat_handlers import (
    search_handler,
    cancel_handler,
    chat_history_retriever,
    chat_handler,
)
from utils.gcal_events import link_handler, unlink_handler, first_signin
from config import return_flow, FIREBASE_TOKEN

import httpx
import asyncio

app = FastAPI()

db = None
try:
    fire_creds = json.loads(FIREBASE_TOKEN)
    cred = credentials.Certificate(fire_creds)
    fapp = initialize_app(cred)
    db = firestore.client()
except Exception as e:
    print(f"Error while connecting to firestore \n{e}")

session = httpx.AsyncClient()
queue = asyncio.Queue()


async def process_queue():
    """Background task to process message edits in a queue.

    Continuously retrieves edit requests from the queue and processes them,
    handling potential errors during message editing.
    """
    while True:
        chat_id, sent_message_id, text, received_message_id = await queue.get()
        try:
            await edit_msg(session, chat_id, sent_message_id, text, received_message_id)
        except Exception as e:
            print(f"Error processing queue item: {e}")
        finally:
            queue.task_done()


@app.get("/api/get_counts")
def get_counts():
    """Endpoint to retrieve dashboard data (user, message, and event counts).

    Returns:
        fastapi.responses.JSONResponse: A JSON response containing event, message,
                                          and user counts.
    """
    result = dashboard_data(db)
    output = {
        "event_count": result[2],
        "message_count": result[1],
        "user_count": result[0],
    }
    return JSONResponse(content=output)


@app.get("/")
def website_return():
    """Serves the TimeSked website HTML content."""
    with open("TimeSked.html", "r") as f:
        html_code = f.read()
    return Response(content=html_code, media_type="text/html")


@app.get("/oauthcallback")
async def oauth_callback(request: fast_request):
    """Handles the OAuth2 callback after user grants Google Calendar access.

    Fetches the authorization code, retrieves user chat ID from the state parameter,
    exchanges the code for tokens, initiates the first-time sign-in process,
    and redirects the user to the TimeSked Telegram bot.

    Args:
        request (fastapi.Request): The incoming FastAPI request object.

    Returns:
        fastapi.responses.RedirectResponse: A redirect response to the TimeSked
                                              Telegram bot.
    """
    try:
        flow = return_flow()

        code = request.query_params.get("code")
        received_state = request.query_params.get("state")

        if not code:
            raise HTTPException(status_code=400, detail="Authorization code missing")

        try:
            chat_id = int(received_state)
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="Invalid state parameter.")

        flow.fetch_token(code=code)

        access_token = flow.credentials.token
        refresh_token = flow.credentials.refresh_token

        asyncio.create_task(first_signin(db, chat_id, access_token, refresh_token))

        success_msg = "Your account has been successfully linked, and a dedicated calendar has been set up. All your events will land right there. 🎯🗓️"
        await send_msg(session, chat_id, None, success_msg, None, None)

        return RedirectResponse("https://t.me/TimeSked_bot")

    except Exception as e:
        print(f"Error in oauth_callback {e}")
        await send_msg(
            session,
            chat_id,
            None,
            "An error occurred, please sign in again",
            None,
            None,
        )
        return None


@app.post("/")
async def index(request: fast_request):
    """Main webhook endpoint for handling incoming Telegram updates.

    Processes incoming messages, photos, commands, and callback queries from Telegram,
    delegating to appropriate handlers based on message type and content.

    Args:
        request (fastapi.Request): The incoming FastAPI request object.

    Returns:
        dict: A dictionary indicating the status of the request.
    """
    try:
        asyncio.create_task(process_queue())
        msg = await request.json()
        sent_message_id = None

        if "message" in msg:
            chat_id = msg["message"]["chat"]["id"]
            received_message_id = msg["message"]["message_id"]
            sent_message_id = None
            try:
                if "photo" in msg["message"]:
                    asyncio.create_task(send_typing_action(session, chat_id))
                    await photo_logic(
                        db, session, msg, chat_id, received_message_id, queue
                    )

                elif "text" in msg["message"]:
                    asyncio.create_task(send_typing_action(session, chat_id))
                    user_message = msg["message"]["text"]

                    col_ref = db.collection("user_records")
                    doc_ref = col_ref.document(str(chat_id))
                    doc = doc_ref.get()
                    position = None
                    calendar_id = None

                    if doc.exists:
                        doc = doc.to_dict()
                        position = doc["position"]
                        calendar_id = doc["calendar_id"]

                    if not position:
                        match user_message:
                            case "/start":
                                await start_handler(
                                    session, msg, chat_id, received_message_id
                                )

                            case "/viewevents":
                                await view_upcoming_events(
                                    db, session, chat_id, sent_message_id
                                )

                            case "/chat":
                                await search_handler(db, session, chat_id)

                            case "/linkcalendar":
                                await link_handler(session, chat_id, calendar_id)

                            case "/unlinkcalendar":
                                await unlink_handler(db, session, chat_id)

                            case "/cancel":
                                await send_msg(
                                    session,
                                    chat_id,
                                    received_message_id,
                                    "Nothing to cancel 👋",
                                )

                            case _:
                                await text_logic(
                                    db,
                                    session,
                                    msg,
                                    chat_id,
                                    received_message_id,
                                    queue,
                                )

                    else:
                        match position:
                            case "DELETING":
                                await unlink_handler(
                                    db,
                                    session,
                                    chat_id,
                                    msg["message"]["text"],
                                    "DELETING",
                                )

                            case "CHATTING":
                                if user_message == "/cancel":
                                    await cancel_handler(db, session, chat_id)
                                else:
                                    prev_msgs = chat_history_retriever(db, chat_id)
                                    await chat_handler(
                                        db,
                                        session,
                                        chat_id,
                                        prev_msgs,
                                        user_message,
                                        received_message_id,
                                    )

            except Exception as e:
                print(
                    "An error has occurred in the index function - whole try except block"
                )
                error_msg = "❌ An error has occurred. Please try again later, Sorry for the inconvenience"

                if not sent_message_id:
                    await send_msg(session, chat_id, received_message_id, error_msg)

                else:
                    await queue.join()
                    await final_edit_msg(
                        session,
                        chat_id,
                        sent_message_id,
                        error_msg,
                        received_message_id,
                    )

                print(f"Error processing message: {e}")

            finally:
                user_handler(db, msg)
                await queue.join()
                return {"ok": True}

        elif "callback_query" in msg:
            try:
                await handle_callback_query(db, session, msg["callback_query"], queue)
            except Exception as e:
                print(f"Error while handling callback query \n {e}")

        else:
            print("Message format not recognized, Neither message nor callback query")

    except Exception as e:
        print(e)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, port=5000)
