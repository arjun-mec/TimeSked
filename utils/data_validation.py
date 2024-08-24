from re import match, sub
import datetime


def date_valid(*dates):
    """Validates if the given date strings are in YYYY-MM-DD format.

    Args:
        *dates: Variable number of date strings.

    Returns:
        bool: True if all date strings are either None or in YYYY-MM-DD format,
              False otherwise.
    """
    valid = []
    for date in dates:
        if date:
            pattern = r"^\d{4}-\d{2}-\d{2}$"
            valid.append(bool(match(pattern, date)))
        else:
            valid.append(True)
    return [True, True] == valid


def time_valid(*times):
    """Validates if the given time strings are in HH:MM format.

    Args:
        *times: Variable number of time strings.

    Returns:
        bool: True if all time strings are either None or in HH:MM format,
              False otherwise.
    """
    valid = []
    for time in times:
        if time:
            pattern = r"^[0-2][0-9]:[0-5][0-9]$"
            valid.append(bool(match(pattern, time)))
        else:
            valid.append(True)
    return [True, True] == valid


def date_cleaner(date_str):
    """Converts a date string in YYYY-MM-DD format to 'Weekday, DD-Month-YYYY' format.

    Args:
        date_str: Date string in YYYY-MM-DD format.

    Returns:
        str: Formatted date string as 'Weekday, DD-Month-YYYY', or the original
             date string if conversion fails.
    """
    try:
        date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        formatted_date = date_obj.strftime("%A, %d-%B-%Y")
        return formatted_date
    except Exception:
        return date_str


def time_cleaner(time_str):
    """Converts a time string in HH:MM:SS format to 'HH:MM AM/PM' format.

    Args:
        time_str: Time string in HH:MM:SS format.

    Returns:
        str: Formatted time string as 'HH:MM AM/PM', or the original time string
             if conversion fails.
    """
    try:
        time_obj = datetime.datetime.strptime(time_str, "%H:%M:%S")
        formatted_time = time_obj.strftime("%I:%M %p")
        return formatted_time
    except Exception:
        return time_str


def escape_markdownv2(text):
    """Escapes MarkdownV2 special characters except within inline URLs.

    Args:
        text: The text to be escaped.

    Returns:
        str: The escaped text with MarkdownV2 special characters protected,
             or the original text if it's empty or None.
    """
    if text:
        escaped_text = sub(
            r"(?<!https://)(?<!http://)[-\.\!\=\#\(\)]", r"\\\g<0>", text
        )
        return escaped_text
    else:
        return text


def process_events(events):
    """Processes and validates event details.

    Args:
        events (list): A list of lists, where each inner list represents an event
                       and contains event details in the order: name, start_date,
                       end_date, start_time, end_time, location, description.

    Returns:
        list: A list of processed events. Each event is represented as a list of
              its details. If an error occurs during processing, the error message
              replaces the event details in the output list.
    """
    processed_events = []

    for event_details in events:
        try:
            # checking if the list has 7 elements
            if len(event_details) != 7:
                raise ValueError(
                    f"Event doesn't have the complete details! Expected 7 got {len(event_details)}."
                )

            # Converting 'None' to None
            for idx, detail in enumerate(event_details):
                if detail == "None":
                    event_details[idx] = None

            flag = 1 if any(event_details) else 0

            # if not start_date => start_date = end_date
            if not event_details[1]:
                event_details[1] = event_details[2]

            # if not start_time => start_time = end_time
            if not event_details[3]:
                event_details[3] = event_details[4]

            # if no end_date, then end_date = start_date
            if not event_details[2]:
                event_details[2] = event_details[1]

            # checking for name
            if not event_details[0]:
                raise ValueError("The message does not contain the name of the event.")

            # checking for date
            if not event_details[1]:
                raise ValueError("The message does not contain the date of the event.")

            if not date_valid(event_details[1], event_details[2]):
                raise ValueError(
                    f"An error occurred while validating dates. {event_details[1]} & {event_details[2]}"
                )

            if not time_valid(event_details[3], event_details[4]):
                raise ValueError(
                    f"An error occurred while validating time. {event_details[3]} & {event_details[4]}"
                )

        except ValueError as e:
            event_details = e

        finally:
            if flag == 1:
                processed_events.append(event_details)

    return processed_events
