from io import BytesIO
from PIL.Image import open as img_open
from config import TOKEN
from utils.weather_info import coordinates_retriever

async def send_msg(session, chat_id, received_message_id, text="Error!", reply_markup=None, parse_mode=None):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": True,
            "reply_to_message_id": received_message_id,
        }

        if parse_mode:
            payload["parse_mode"] = parse_mode
        
        if reply_markup:
            payload["reply_markup"] = reply_markup

        response = await session.post(url, json=payload)

        if response.status_code != 200:
            print("Error : ", response.text)

            # try without parse mode
            await send_msg(session, chat_id, received_message_id, text, reply_markup)

            return None

        return response

    except Exception as e:
        print(f"An error has occurred in send_msg : {e}")


async def final_edit_msg(
        session, chat_id, sent_message_id, text, received_message_id, location=None, coords=None, parse_mode=None
):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/editMessageText"
        payload = {
            "chat_id": chat_id,
            "message_id": sent_message_id,
            "text": text,
            "disable_web_page_preview": True,
            "reply_to_message_id": received_message_id,
            "reply_markup": {
                "inline_keyboard": [
                    [
                        {
                            "text": "🔁 Regenerate",
                            "callback_data": "RE^!" + str(received_message_id),
                        }
                    ]
                ]
            },
        }

        if coords is not None:
            payload["reply_markup"]["inline_keyboard"].append(
                [{"text": "📍 Location", "callback_data": "L0C@" + location}]
            )
        
        if parse_mode is not None:
            payload["parse_mode"] = parse_mode

        response = await session.post(url, json=payload)

        if response.status_code != 200:
            print("Error : ", response.text)

            # try without parse mode
            await final_edit_msg(session, chat_id, sent_message_id, text, received_message_id, location, coords, None)

        return response

    except Exception as e:
        print(f"Error in final_edit_msg {e}")


async def edit_msg(session, chat_id, sent_message_id, text, received_message_id=None, reply_markup=None, parse_mode=None):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/editMessageText"
        payload = {
            "chat_id": chat_id,
            "message_id": sent_message_id,
            "text": text,
            "disable_web_page_preview": True,
            "reply_to_message_id": received_message_id,
        }

        if parse_mode is not None:
            payload["parse_mode"] = parse_mode

        if reply_markup:
            payload["reply_markup"] = reply_markup

        response = await session.post(url, json=payload)
        
        if response.status_code != 200:
            print("Error : ", response.text)

            #try without parsing mode
            await edit_msg(session, chat_id, sent_message_id, text, received_message_id, reply_markup, None)
        
        return response

    except Exception as e:
        print(f"An error has occurred in edit_msg : {e}")


async def pin_msg(session, chat_id, message_id):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/pinChatMessage"
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
        }

        response = await session.post(url, json=payload)

        if response.status_code != 200:
            print("Error : ", response.text)

        return response

    except Exception as e:
        print(f"An error has occurred in pin_msg : {e}")


async def unpin_msg(session, chat_id):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/unpinChatMessage"
        payload = {
            "chat_id": chat_id,
        }

        response = await session.post(url, json=payload)

        if response.status_code != 200:
            print("Error : ", response.text)
        
        return response

    except Exception as e:
        print(f"An error has occurred in unpin_msg : {e}")


async def send_typing_action(session, chat_id):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendChatAction"
        payload = {"chat_id": chat_id, "action": "typing"}

        response = await session.post(url, json=payload)

        if response.status_code != 200:
            print("Error : ", response.text)
        
        return response
    
    except Exception as e:
        print(f"An error has occurred in send_typing_action : {e}")


async def send_location_action(session, chat_id):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendChatAction"
        payload = {"chat_id": chat_id, "action": "find_location"}

        response = await session.post(url, json=payload)

        if response.status_code != 200:
            print("Error : ", response.text)

        return response
    
    except Exception as e:
        print(f"An error has occurred in send_location_action : {e}")


async def send_venue(session, chat_id, location):
    """sends the venue where the event is being held"""
    try:
        details = await coordinates_retriever(session, location)

        url = f"https://api.telegram.org/bot{TOKEN}/sendVenue"

        data = {
            "chat_id": chat_id,
            "latitude": details["latitude"],
            "longitude": details["longitude"],
            "title": details["name"],
            "address": details["address"],
        }

        await session.post(url, json=data)

    except Exception as e:
        print(f"Error while sending venue {e}")


async def image_downloader(session, file_id):
    """downloads the image using its file id"""
    file_path_response = await session.get(
        f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={file_id}"
    )
    file_path = file_path_response.json()["result"]["file_path"]

    image_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
    image_response = await session.get(image_url, timeout=10.0)

    image_bytes = BytesIO(image_response.content)
    image = img_open(image_bytes)

    return image

