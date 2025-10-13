import os
import json
import datetime
from typing import Optional

from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from langchain_core.tools import tool

from api.core.config import SCOPES, TOKEN_PATH

def _get_calendar_credentials() -> Optional[Credentials]:
    """
    Loads Google Calendar credentials from an environment variable or a local file.
    For production (Vercel), the GOOGLE_TOKEN_JSON environment variable should be used.
    """
    creds = None
    print("---[AUTH] Starting to fetch calendar credentials.")
    token_json_str = os.getenv("GOOGLE_TOKEN_JSON")

    if token_json_str:
        # Load from environment variable (ideal for Vercel)
        try:
            token_info = json.loads(token_json_str)
            creds = Credentials.from_authorized_user_info(token_info, SCOPES)
            print("---[AUTH] Credentials loaded from GOOGLE_TOKEN_JSON environment variable.")
        except json.JSONDecodeError:
            print("---[AUTH-ERROR] The GOOGLE_TOKEN_JSON environment variable is not valid JSON.")
            return None
    elif os.path.exists(TOKEN_PATH):
        # Load from local file (for development or first-time authentication)
        print(f"---[AUTH] Attempting to load credentials from local file: {TOKEN_PATH}")
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
        print("---[AUTH] Credentials loaded from local file.")

    # If credentials don't exist or are not valid, try to refresh them
    if not creds or not creds.valid:
        print("---[AUTH] Credentials not found or not valid.")
        if creds and creds.expired and creds.refresh_token:
            print("---[AUTH] Credentials expired. Attempting to refresh token...")
            try:
                creds.refresh(GoogleRequest())
                print("---[AUTH] Token refreshed successfully.")
                # IMPORTANT: If the token is refreshed, the new state will not be saved
                # to the environment variable automatically. The `refresh_token` is still
                # valid, so it will work on the next execution.
            except Exception as e:
                print(f"Error refreshing token: {e}")
                return None
        else:
            print("---[AUTH-ERROR] No valid credentials or refresh_token. Manual authentication required.")
            # No credentials or refresh token, authentication is needed.
            return None
    
    print("---[AUTH] Valid credentials obtained.")
    return creds

@tool
def get_calendar_events(days_from_now: int) -> str:
    """Searches Google Calendar for events in the next 'days_from_now' days."""
    print(f"---[TOOL] Executing get_calendar_events for the next {days_from_now} days.")
    creds = _get_calendar_credentials()
    if not creds:
        print("---[TOOL-ERROR] Could not get credentials for get_calendar_events.")
        return "Error: The user is not authenticated. Please authorize access to your calendar."
    
    try:
        service = build("calendar", "v3", credentials=creds)
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        future_date = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=days_from_now)).isoformat()
        
        print(f"---[TOOL] Searching for events between {now} and {future_date}")
        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=now,
                timeMax=future_date,
                maxResults=10,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        events = events_result.get("items", [])

        if not events:
            print(f"---[TOOL] No events found.")
            return f"No events found in the next {days_from_now} days."

        print(f"---[TOOL] Found {len(events)} events.")
        event_list = []
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            event_list.append(f"- {event['summary']} (Start: {start})")
        response = "Found events:\n" + "\n".join(event_list)
        print(f"---[TOOL] Tool response: {response}")
        return response

    except HttpError as error:
        print(f"---[TOOL-ERROR] HttpError with Google Calendar API: {error}")
        return f"An error occurred with the Google Calendar API: {error}"
    except Exception as e:
        return f"An unexpected error occurred: {e}"