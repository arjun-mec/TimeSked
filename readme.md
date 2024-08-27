## TimeSked - Your Telegram Calendar Assistant

TimeSked is a Telegram bot that makes scheduling events effortless. Send TimeSked a message describing your event, and it will extract the details and help you add it to your Google Calendar.

**Overview Video :** [https://www.youtube.com/watch?v=rZlUvHB2BcA&pp=ygUIVGltZVNLZWQ%3D](https://www.youtube.com/watch?v=rZlUvHB2BcA&pp=ygUIVGltZVNLZWQ%3D)

### Features:

- **Event Extraction:** TimeSked uses advanced AI to understand event details from text messages or even images!
- **Google Calendar Integration:** Connect your Google Calendar to TimeSked for seamless event creation.
- **Pre-filled Event Links:** Even without linking your calendar, TimeSked generates pre-filled Google Calendar event links for quick scheduling.
- **Weather-Based Suggestions:** TimeSked provides clothing suggestions based on the weather forecast for your event location.
- **Chat Mode:** Ask TimeSked questions about your upcoming events in a natural, conversational way.

### Try It Out:

- **Telegram Bot:** [Telegram Bot Link](https://t.me/TimeSked_bot)
- **Website:** [Dashboard Website Link](https://timesked.koyeb.app/)

### How It Works:

1. **Send an Event Message:** Describe your event in a text message or send a screenshot containing event details.
2. **Event Extraction:** TimeSked's AI extracts event name, date, time, location, and description.
3. **Calendar Interaction:** If you've linked your Google Calendar, the event is automatically added. Otherwise, TimeSked provides a pre-filled event link.
4. **Weather Suggestions:** For single events with a location, TimeSked fetches the weather forecast and suggests appropriate clothing.

### Commands:

- `/start`: Start a conversation with TimeSked.
- `/viewevents`: View your upcoming events.
- `/chat`: Enter chat mode to ask questions about your events.
- `/linkcalendar`: Link your Google Calendar to TimeSked.
- `/unlinkcalendar`: Unlink your Google Calendar from TimeSked.
- `/cancel`: Exit chat mode or cancel an operation.

### Technology Stack:

- **FastAPI:** Python web framework for building the API.
- **Google Gemini:** Advanced AI model for event extraction and chat functionality.
- **Google Calendar API:** For event creation, deletion, and retrieval.
- **Visual Crossing Weather API:** For fetching weather forecasts.
- **Firebase:** Cloud database for storing user data and event information.
- **httpx:** Asynchronous HTTP client for interacting with APIs.

Feel free to explore the code and contribute to make TimeSked even better!
