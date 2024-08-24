from ast import literal_eval

from config import text_model, img_model, query


def prompter(type, message):
    """Sends a prompt to the Gemini model to extract event details.

    This function handles both text and image-based prompts, processes the model's
    response, attempts to convert it into a list of events, and handles potential errors.

    Args:
        type (str): The type of message ("text" or "image").
        message (str or bytes): The message content (text or image data).

    Returns:
        list or str: If successful, returns a list of lists, where each inner list
                      represents an event and contains its details. If an error occurs
                      or the model's response is invalid, returns an appropriate
                      error message string.
    """
    try:
        if type == "text":
            response = text_model.generate_content(f"{query} {message}")
        else:
            response = img_model.generate_content([message, query])

        details = response.text.replace("\n", "")
        print(f"Model Response : {details}")

        # Converting to list
        e = None
        events = None
        for i in range(2):
            try:
                events = literal_eval(details.strip())
                break
            except SyntaxError as e:
                if "unterminated string literal" in str(e):
                    if type == "text":
                        response = text_model.generate_content(f"{query} {message}")
                    else:
                        response = img_model.generate_content([message, query])

                    details = response.text.replace("\n", "")

        if isinstance(events, list):
            if len(events) == 0:
                return events

            else:
                if isinstance(events[0], str):
                    new_events = []
                    new_events.append(events)
                    events = new_events

                return events

        else:
            return f"❌ An error has occurred. Error with model response {details}"

    except ValueError as ve:
        return f"ValueError: {ve}. Please check your input and try again."
    except Exception as e:
        print(f"An Error has occurred in the text_prompter function \n{e}.")

    return "❌ An error has occurred while prompting the gemini model. Please try again later"
