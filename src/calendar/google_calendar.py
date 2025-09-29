from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta

class GoogleCalendar:
    def __init__(self, credentials_file):
        self.credentials = service_account.Credentials.from_service_account_file(credentials_file)
        self.service = build('calendar', 'v3', credentials=self.credentials)

    def list_events(self, calendar_id='primary', time_min=None, time_max=None):
        if time_min is None:
            time_min = datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
        if time_max is None:
            time_max = (datetime.utcnow() + timedelta(days=30)).isoformat() + 'Z'  # 30 days from now

        events_result = self.service.events().list(calendarId=calendar_id, timeMin=time_min, timeMax=time_max,
                                                   singleEvents=True, orderBy='startTime').execute()
        events = events_result.get('items', [])
        return events

    def create_event(self, calendar_id='primary', event_details=None):
        if event_details is None:
            return None

        event = {
            'summary': event_details.get('summary'),
            'location': event_details.get('location'),
            'description': event_details.get('description'),
            'start': {
                'dateTime': event_details.get('start'),
                'timeZone': event_details.get('timeZone', 'UTC'),
            },
            'end': {
                'dateTime': event_details.get('end'),
                'timeZone': event_details.get('timeZone', 'UTC'),
            },
        }

        event = self.service.events().insert(calendarId=calendar_id, body=event).execute()
        return event

    def delete_event(self, calendar_id='primary', event_id=None):
        if event_id is None:
            return None

        self.service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
        return True