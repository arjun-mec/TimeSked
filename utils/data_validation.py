from re import match, sub
import datetime


def date_valid(*dates):
    valid = []
    for date in dates:
        if date:
            pattern = r"^\d{4}-\d{2}-\d{2}$"
            valid.append(bool(match(pattern, date)))
        else:
            valid.append(True)
    return [True, True] == valid


def time_valid(*times):
    valid = []
    for time in times:
        if time:
            pattern = r"^[0-2][0-9]:[0-5][0-9]$"
            valid.append(bool(match(pattern, time)))
        else:
            valid.append(True)
    return [True, True] == valid


def date_cleaner(date_str):
    try:
        date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        formatted_date = date_obj.strftime("%A, %d-%B-%Y")
        return formatted_date
    except Exception:
        return date_str
    

def time_cleaner(time_str):
    try:
        time_obj = datetime.datetime.strptime(time_str, "%H:%M:%S")
        formatted_time = time_obj.strftime("%I:%M %p")
        return formatted_time
    except Exception:
        return time_str
    

def escape_markdownv2(text):
    """Escapes MarkdownV2 special characters except within inline URLs."""
    if text:
        escaped_text = sub(r'(?<!https://)(?<!http://)[-\.\!\=\#\(\)]', r'\\\g<0>', text)
        return escaped_text
    else:
        return text


def process_events(events): 
    processed_events = []
   
    for event_details in events:
        try:
            # checking if the list has 7 elements
            if len(event_details) != 7:
                raise ValueError(f"Event doesn't have the complete details ! Excepted 7 got {len(event_details)}.")
            
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
                raise ValueError(f"An error occurred while validating dates. {event_details[1]} & {event_details[2]}")
            
            if not time_valid(event_details[3], event_details[4]):
                raise ValueError(f"An error occurred while validating time. {event_details[3]} & {event_details[4]}")
    
        except ValueError as e:
            event_details = e
        
        finally:
            if flag == 1:
                processed_events.append(event_details)
    
    return processed_events

