import os
import json
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Security
from pydantic import BaseModel

from api.core.security import get_api_key

from api.services.agent import graph_app, setup_retriever
import firebase_admin
from firebase_admin import credentials
from google.cloud import firestore as google_firestore

router = APIRouter()

# This is a simplified way to handle the db dependency.
# In a larger app, you might want to use a more robust dependency injection system.
db = None

def get_db():
    global db
    if db is None:
        try:
            cred_json_str = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
            if cred_json_str:
                cred_info = json.loads(cred_json_str)
                cred = credentials.Certificate(cred_info)
                
                if not firebase_admin._apps:
                    firebase_admin.initialize_app(cred)
                
                google_auth_creds = cred.get_credential()

                project_id = firebase_admin.get_app().project_id

                db = google_firestore.Client(project=project_id, database="chatbot-hilos", credentials=google_auth_creds)
                
                print("Firebase Admin SDK initialized successfully.")
            else:
                print("WARNING: 'FIREBASE_SERVICE_ACCOUNT_JSON' environment variable not set. Chat memory (Firestore) will not work.")
        except Exception as e:
            print(f"ERROR: Could not initialize Firebase Admin SDK: {e}")
    return db


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

@router.post("/chatbot")
async def handle_chat(request: ChatRequest, db=Depends(get_db), api_key: str = Security(get_api_key)):
    print("\n---[API] Entering handle_chat ---")
    try:
        if not db:
            print("---[API-ERROR] Database connection (db) not available.")
            raise HTTPException(status_code=500, detail="Database service (Firestore) not available.")

        session_id = request.session_id
        print(f"---[API] Session ID received: {session_id}")
        chat_history_tuples = []

        if session_id:
            doc_ref = db.collection("chat_sessions").document(session_id)
            doc = doc_ref.get()
            if doc.exists:
                history_from_db = doc.to_dict().get("history", [])
                chat_history_tuples = [(item.get("role"), item.get("content")) for item in history_from_db]
                print(f"---[API] Chat history retrieved for session {session_id}: {len(chat_history_tuples)} turns.")
            else:
                print(f"---[API] No history found for session {session_id}.")
        else:
            doc_ref = db.collection("chat_sessions").document() # This creates a reference, not the document
            session_id = doc_ref.id
            print(f"---[API] New session created with ID: {session_id}")

        inputs = {"question": request.message, "chat_history": chat_history_tuples, "form_data": {}}
        print(f"---[API] Input for the graph: {{'question': '{request.message}', 'chat_history_length': {len(chat_history_tuples)}}}")
        
        result = graph_app.invoke(inputs)
        
        generation_data = result.get("generation", {})
        
        reply_text = generation_data.get("reply", "Could not generate a response.")
        form_data = generation_data.get("formData", {})
        print(f"---[API] Generation received from graph: {reply_text[:80]}...")
        print(f"---[API] Form data extracted: {form_data}")

        updated_history_tuples = chat_history_tuples + [("user", request.message), ("assistant", reply_text)]
        history_for_db = [{"role": role, "content": content} for role, content in updated_history_tuples]

        print(f"---[API] Saving new history with {len(history_for_db)} turns in session {session_id}.")
        doc_ref.set({"history": history_for_db}, merge=True)
        print("---[API] History saved successfully.")

        response_data = {
            "reply": reply_text,
            "session_id": session_id,
            "formData": form_data
        }
        print(f"---[API] Sending response: {response_data}")
        return response_data
    except Exception as e:
        print(f"---[API-CRITICAL-ERROR] An unhandled exception occurred in handle_chat: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")
