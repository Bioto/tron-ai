
DEFAULT_SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.send"
]
    
    
def get_gmail_service(scopes=None):
    """
    Returns an authenticated Gmail API service using OAuth2 credentials.
    Handles token.json and client_secret JSON as in test_gmail.py.
    Args:
        scopes (list): List of OAuth scopes. Defaults to Gmail readonly if None.
    Returns:
        googleapiclient.discovery.Resource: Authenticated Gmail API service
    """
    import os
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

 
    if scopes is None:
        scopes = DEFAULT_SCOPES
    creds = None
    token_path = os.path.join(os.path.dirname(__file__), "../../../token.json")
    client_secret_path = os.path.join(os.path.dirname(__file__), "../../../.secrets/client_secret_487115951073-h6fn2voj96eaukne7h88hllh8ffjhpu9.apps.googleusercontent.com.json")
    token_path = os.path.abspath(token_path)
    client_secret_path = os.path.abspath(client_secret_path)
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, scopes)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, scopes)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w") as token:
            token.write(creds.to_json())
    service = build("gmail", "v1", credentials=creds)
    return service

def get_calendar_service(scopes=None):
    """
    Returns an authenticated Google Calendar API service using OAuth2 credentials.
    Handles token.json and client_secret JSON as in get_gmail_service.
    Args:
        scopes (list): List of OAuth scopes. Defaults to Calendar readonly if None.
    Returns:
        googleapiclient.discovery.Resource: Authenticated Calendar API service
    """
    import os
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build


    if scopes is None:
        scopes = DEFAULT_SCOPES
    creds = None
    token_path = os.path.join(os.path.dirname(__file__), "../../../token.json")
    client_secret_path = os.path.join(os.path.dirname(__file__), "../../../.secrets/client_secret_487115951073-h6fn2voj96eaukne7h88hllh8ffjhpu9.apps.googleusercontent.com.json")
    token_path = os.path.abspath(token_path)
    client_secret_path = os.path.abspath(client_secret_path)
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, scopes)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, scopes)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w") as token:
            token.write(creds.to_json())
    service = build("calendar", "v3", credentials=creds)
    return service