import os
import json
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import InstalledAppFlow

from api.core.config import BASE_URL, SCOPES, CREDENTIALS_PATH, TOKEN_PATH

router = APIRouter()

def _get_google_auth_flow():
    """Creates a Flow instance for the web authentication flow."""
    creds_json_str = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if creds_json_str:
        try:
            client_config = json.loads(creds_json_str)
            return InstalledAppFlow.from_client_config(client_config, SCOPES)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=500, detail=f"Error decoding GOOGLE_CREDENTIALS_JSON: {e}")

    elif os.path.exists(CREDENTIALS_PATH):
        return InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
    else:
        raise HTTPException(
            status_code=500, 
            detail=f"Credentials file ('{CREDENTIALS_PATH}') not found, and 'GOOGLE_CREDENTIALS_JSON' environment variable is not set."
        )

@router.get("/auth/google")
def auth_google():
    print("---[API] Initiating authentication flow at /api/auth/google")
    flow = _get_google_auth_flow()
    flow.redirect_uri = f"{BASE_URL}/api/oauth2callback"
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'  # Forces consent screen and refresh_token
    )
    print(f"---[API] Redirecting user to: {authorization_url}")
    return RedirectResponse(authorization_url)

@router.get("/oauth2callback")
def oauth2callback(request: Request):
    print("---[API] Received callback at /api/oauth2callback")
    flow = _get_google_auth_flow()
    flow.redirect_uri = f"{BASE_URL}/api/oauth2callback"
    try:
        print("---[API] Attempting to fetch authorization token.")
        flow.fetch_token(authorization_response=str(request.url))
        creds = flow.credentials
        print("---[API] Token fetched successfully.")

        # Save the token to a local file. This file is to get the
        # content that you will then put in the GOOGLE_TOKEN_JSON environment variable.
        print(f"---[API] Saving credentials to {TOKEN_PATH}")
        with open(TOKEN_PATH, 'w') as token_file:
            token_file.write(creds.to_json())
        print("---[API] Credentials saved. Authentication complete.")
        return {"message": "Authentication completed successfully. You can now close this window."}
    except Exception as e:
        print(f"---[API-ERROR] Error in authentication callback: {e}")
        raise HTTPException(status_code=500, detail=f"Error in authentication: {e}")
