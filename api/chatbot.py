import os
import uvicorn
import json
import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import List, Dict, Any, TypedDict, Optional, Sequence

# Imports de Google Auth y Calendar (usaremos Flow en lugar de InstalledAppFlow)
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Imports de LangChain y LangGraph
from langchain_community.document_loaders import UnstructuredMarkdownLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode
from langgraph.graph import StateGraph, END

# Imports de Firebase
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud import firestore as google_firestore

from dotenv import load_dotenv

# --- 1. Configuración Global y Carga de Entorno ---
load_dotenv()

# Configuración de Google Calendar OAuth
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
TOKEN_PATH = "token.json"
CREDENTIALS_PATH = "credentials.json"

# Instancia de la aplicación FastAPI
app = FastAPI()

# --- Configuración de CORS (Cross-Origin Resource Sharing) ---
# Esto es crucial para permitir que tu frontend se comunique con esta API.

# Lista de orígenes permitidos.
# Añade la URL donde se ejecuta tu frontend en desarrollo y producción.
origins = [
    "http://localhost",      # Origen base
    "http://localhost:3000", # Para React (Create React App)
    "http://localhost:5173", # Para Vite (React, Vue)
    # Si tu frontend está en Vercel, añade su URL aquí también.
    # Ejemplo: "https://mi-frontend-chatbot.vercel.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Permite todos los métodos (GET, POST, etc.)
    allow_headers=["*"],  # Permite todas las cabeceras
)

# Determinar la URL base según el entorno
if os.getenv("VERCEL"):
    # Entorno de producción en Vercel. Vercel establece esta variable.
    BASE_URL = f"https://{os.getenv('VERCEL_URL')}"
else:
    # Entorno de desarrollo local
    BASE_URL = "http://localhost:8000"

# Variables globales para el RAG
vectorstore = None
retriever = None
db = None

# --- 2. Herramientas del Agente ---
def _get_calendar_credentials() -> Optional[Credentials]:
    """
    Carga las credenciales de Google Calendar desde una variable de entorno o un archivo local.
    Para producción (Vercel), se debe usar la variable de entorno GOOGLE_TOKEN_JSON.
    """
    creds = None
    print("---[AUTH] Iniciando obtención de credenciales de calendario.")
    token_json_str = os.getenv("GOOGLE_TOKEN_JSON")

    if token_json_str:
        # Cargar desde la variable de entorno (ideal para Vercel)
        try:
            token_info = json.loads(token_json_str)
            creds = Credentials.from_authorized_user_info(token_info, SCOPES)
            print("---[AUTH] Credenciales cargadas desde la variable de entorno GOOGLE_TOKEN_JSON.")
        except json.JSONDecodeError:
            print("---[AUTH-ERROR] La variable de entorno GOOGLE_TOKEN_JSON no es un JSON válido.")
            return None
    elif os.path.exists(TOKEN_PATH):
        # Cargar desde el archivo local (para desarrollo o la primera autenticación)
        print(f"---[AUTH] Intentando cargar credenciales desde el archivo local: {TOKEN_PATH}")
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
        print("---[AUTH] Credenciales cargadas desde archivo local.")

    # Si las credenciales no existen o no son válidas, intenta refrescarlas
    if not creds or not creds.valid:
        print("---[AUTH] Credenciales no encontradas o no válidas.")
        if creds and creds.expired and creds.refresh_token:
            print("---[AUTH] Credenciales expiradas. Intentando refrescar token...")
            try:
                creds.refresh(GoogleRequest())
                print("---[AUTH] Token refrescado con éxito.")
                # IMPORTANTE: Si el token se refresca, el nuevo estado no se guardará
                # en la variable de entorno automáticamente. El `refresh_token` sigue
                # siendo válido, por lo que funcionará en la próxima ejecución.
            except Exception as e:
                print(f"Error refreshing token: {e}")
                return None
        else:
            print("---[AUTH-ERROR] No hay credenciales válidas ni refresh_token. Se requiere autenticación manual.")
            # No hay credenciales o refresh token, se necesita autenticación.
            return None
    
    print("---[AUTH] Credenciales válidas obtenidas.")
    return creds

@tool
def get_calendar_events(days_from_now: int) -> str:
    """Busca en Google Calendar los eventos para los próximos 'days_from_now' días."""
    print(f"---[TOOL] Ejecutando get_calendar_events para los próximos {days_from_now} días.")
    creds = _get_calendar_credentials()
    if not creds:
        print("---[TOOL-ERROR] No se pudieron obtener las credenciales para get_calendar_events.")
        return "Error: El usuario no está autenticado. Por favor, necesita autorizar el acceso a su calendario."
    
    try:
        service = build("calendar", "v3", credentials=creds)
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        future_date = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=days_from_now)).isoformat()
        
        print(f"---[TOOL] Buscando eventos entre {now} y {future_date}")
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
            print(f"---[TOOL] No se encontraron eventos.")
            return f"No se encontraron eventos en los próximos {days_from_now} días."

        print(f"---[TOOL] Se encontraron {len(events)} eventos.")
        event_list = []
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            event_list.append(f"- {event['summary']} (Inicio: {start})")
        response = "Eventos encontrados:\n" + "\n".join(event_list)
        print(f"---[TOOL] Respuesta de la herramienta: {response}")
        return response

    except HttpError as error:
        print(f"---[TOOL-ERROR] HttpError con la API de Google Calendar: {error}")
        return f"Ocurrió un error con la API de Google Calendar: {error}"
    except Exception as e:
        return f"Ocurrió un error inesperado: {e}"

@tool
def search_event_info(query: str) -> str:
    """Busca información sobre los servicios, precios y detalles de los eventos de NonaEventos."""
    print(f"---[TOOL] Ejecutando search_event_info con la consulta: {query}")
    if retriever:
        relevant_docs = retriever.get_relevant_documents(query)
        if relevant_docs:
            context = "\n\n".join(doc.page_content for doc in relevant_docs)
            print(f"---[TOOL] Contexto RAG encontrado: {context[:200]}...")
            return f"Información relevante encontrada:\n{context}"
    return "No se encontró información relevante."

tools = [get_calendar_events, search_event_info]

class AgentState(TypedDict):
    question: str
    chat_history: Sequence[tuple]
    generation: Any
    tool_calls: List[Dict[str, Any]]
    tool_output: Optional[Dict[str, Any]]

def should_call_tools(state: AgentState) -> str:
    """Determina si el agente debe llamar a una herramienta."""
    print("\n---[GRAPH] Nodo: should_call_tools ---")
    if state.get("tool_calls"):
        print("---[GRAPH] Decisión: SÍ se necesitan herramientas. -> Redirigiendo a 'tools'")
        return "tools"
    else:
        print("---[GRAPH] Decisión: NO se necesitan herramientas. -> Redirigiendo a 'responder'")
        return "responder"

def call_model(state: AgentState):
    print("\n---[GRAPH] Nodo: agent (call_model) ---")
    print(f"---[GRAPH] Pregunta del usuario: {state['question']}")
    
    # Asegurarse de que el historial de chat esté en el formato correcto (lista de tuplas)
    chat_history = state.get('chat_history', [])
    
    messages = [("system", "Eres un asistente virtual para NonaEventos. Responde a las preguntas del usuario de forma amable y servicial. Puedes usar las herramientas disponibles para obtener información.")]
    messages.extend(chat_history)
    messages.append(("user", state['question']))
    
    llm = ChatGoogleGenerativeAI(model="models/gemini-pro-latest", temperature=0).bind_tools(tools)
    response = llm.invoke(messages)
    print(f"---[GRAPH] Respuesta del modelo (con tool_calls): {response.tool_calls}")
    return {"tool_calls": response.tool_calls}

def call_tools(state: AgentState):
    print("\n---[GRAPH] Nodo: tools (call_tools) ---")
    tool_map = {tool.name: tool for tool in tools}
    output = {}
    for call in state["tool_calls"]:
        tool_name = call["name"]
        tool_args = call["args"]
        print(f"---[GRAPH] Ejecutando herramienta: '{tool_name}' con argumentos: {tool_args}")
        if tool_name in tool_map:
            try:
                output[tool_name] = tool_map[tool_name].invoke(tool_args)
                print(f"---[GRAPH] Resultado de '{tool_name}': {output[tool_name]}")
            except Exception as e:
                output[tool_name] = f"Error al ejecutar la herramienta {tool_name}: {e}"
    return {"tool_output": output}

def generate_final_answer(state: AgentState):
    print("---GENERANDO RESPUESTA FINAL Y EXTRAYENDO DATOS---")
    question = state['question']
    chat_history = state['chat_history']
    tool_output_dict = state.get('tool_output')

    # Construir una representación legible de la salida de las herramientas
    if tool_output_dict:
        tool_output_str = "\n".join(f"- {tool}: {output}" for tool, output in tool_output_dict.items())
    else:
        tool_output_str = "No se utilizaron herramientas en este turno."

    # Prompt del sistema para guiar al modelo
    system_prompt = """Eres un asistente virtual para NonaEventos. Tu objetivo es doble:
1.  **Conversar amablemente**: Responde a la pregunta del usuario basándote en el historial y la salida de las herramientas.
2.  **Extraer datos**: Rellena un formulario con la información que proporcione el usuario.

**Instrucciones para la extracción de datos:**
-   `name`: El nombre completo del usuario.
-   `email`: La dirección de correo electrónico del usuario.
-   `phone`: El número de teléfono del usuario.
-   `eventType`: El tipo de evento. Debe ser uno de: "Wedding", "Birthday / Social", "Corporate", "Other".
-   `message`: Un resumen conciso de la solicitud del usuario en 1-2 frases cortas.

**Formato de Salida Obligatorio:**
Tu respuesta final DEBE ser un bloque de código JSON válido. El objeto JSON debe tener dos claves:
1.  `reply`: (string) Tu respuesta conversacional al usuario.
2.  `formData`: (JSON object) Un objeto con los campos que has extraído. Si un campo aún no se conoce, no lo incluyas o déjalo como null.
"""

    # Construir la lista de mensajes para el modelo
    messages = [("system", system_prompt)]
    
    # Añadir el historial de chat si existe
    if chat_history:
        messages.extend(chat_history)
        
    # Añadir la salida de las herramientas si existe
    if tool_output_dict:
        tool_output_message = f"Herramientas usadas:\n{tool_output_str}"
        messages.append(("system", tool_output_message))

    # Añadir la pregunta actual del usuario
    messages.append(("user", question))
    
    # Añadir la instrucción final para el formato de respuesta
    messages.append(("system", "**Tu Respuesta (solo el bloque de código JSON):**"))

    llm = ChatGoogleGenerativeAI(model="models/gemini-pro-latest", temperature=0.1)
    
    # Invocamos el modelo directamente con la lista de mensajes
    response = llm.invoke(messages)
    raw_response = response.content if response.content else ""


    # Log a prueba de errores de codificación
    safe_raw_response = raw_response.encode('utf-8', 'ignore').decode('utf-8')
    print(f"---[GRAPH] Respuesta CRUDA del modelo: {safe_raw_response}")

    try:
        # Limpiar la respuesta para encontrar el JSON
        json_block = raw_response.strip().replace("```json", "").replace("```", "").strip()
        if not json_block:
            # Si el bloque está vacío después de limpiar, devuelve una respuesta predeterminada
            return {"generation": {"reply": "No he podido procesar tu solicitud. ¿Podrías intentarlo de nuevo?", "formData": {}}}
        parsed_json = json.loads(json_block)
        print(f"---[GRAPH] JSON analizado con éxito.")
        return {"generation": parsed_json}
    except Exception as e:
        print(f"---[GRAPH-ERROR] No se pudo analizar el JSON de la respuesta de la IA: {e}")
        # Devolver la respuesta cruda si el análisis JSON falla
        return {"generation": {"reply": raw_response, "formData": {}}}


# --- 4. Construcción del Grafo y la API ---

# RAG retriever setup
def setup_retriever():
    global vectorstore, retriever
    doc_path = os.path.join(os.path.dirname(__file__), '..', 'docs', 'info_eventos.md')
    if not os.path.exists(doc_path):
        raise FileNotFoundError(f"El archivo de conocimiento no se encontró en: {doc_path}")
    loader = UnstructuredMarkdownLoader(doc_path)
    docs = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splits = text_splitter.split_documents(docs)
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    vectorstore = FAISS.from_documents(splits, embeddings)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
    print("Retriever configurado y listo.")

# Construir el grafo del agente
workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model)
workflow.add_node("tools", call_tools)
workflow.add_node("responder", generate_final_answer)

workflow.set_entry_point("agent")
workflow.add_conditional_edges(
    "agent",
    should_call_tools,
    {
        "tools": "tools",
        "responder": "responder",
    }
)
workflow.add_edge("tools", "responder")
workflow.add_edge("responder", END)
graph_app = workflow.compile()

# Endpoints de la API
@app.on_event("startup")
async def startup_event():
    global db
    setup_retriever()
    # Inicializar Firebase Admin SDK
    try:
        cred_json_str = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
        if cred_json_str:
            cred_info = json.loads(cred_json_str)
            cred = credentials.Certificate(cred_info)
            
            # Inicializar firebase_admin
            firebase_admin.initialize_app(cred)
            
            # Obtener las credenciales de google.auth subyacentes
            google_auth_creds = cred.get_credential()

            # Obtener el project ID de la app inicializada
            project_id = firebase_admin.get_app().project_id

            # Pasar las credenciales explícitamente al cliente de Firestore
            db = google_firestore.Client(project=project_id, database="chatbot-hilos", credentials=google_auth_creds)
            
            print("Firebase Admin SDK inicializado con éxito.")
        else:
            print("ADVERTENCIA: La variable de entorno 'FIREBASE_SERVICE_ACCOUNT_JSON' no está configurada. La memoria del chat (Firestore) no funcionará.")
    except Exception as e:
        print(f"ERROR: No se pudo inicializar Firebase Admin SDK: {e}")


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

@app.post("/api/chatbot")
async def handle_chat(request: ChatRequest):
    print("\n---[API] Entrando a handle_chat ---")
    try:
        if not db:
            print("---[API-ERROR] La conexión a la base de datos (db) no está disponible.")
            raise HTTPException(status_code=500, detail="El servicio de base de datos (Firestore) no está disponible.")

        session_id = request.session_id
        print(f"---[API] Session ID recibido: {session_id}")
        chat_history_tuples = []

        if session_id:
            doc_ref = db.collection("chat_sessions").document(session_id)
            doc = doc_ref.get()
            if doc.exists:
                history_from_db = doc.to_dict().get("history", [])
                chat_history_tuples = [(item.get("role"), item.get("content")) for item in history_from_db]
                print(f"---[API] Historial de chat recuperado para la sesión {session_id}: {len(chat_history_tuples)} turnos.")
            else:
                print(f"---[API] No se encontró historial para la sesión {session_id}.")
        else:
            doc_ref = db.collection("chat_sessions").document() # Esto crea una referencia, no el documento
            session_id = doc_ref.id
            print(f"---[API] Nueva sesión creada con ID: {session_id}")

        inputs = {"question": request.message, "chat_history": chat_history_tuples, "form_data": {}}
        print(f"---[API] Entrada para el grafo: {{'question': '{request.message}', 'chat_history_length': {len(chat_history_tuples)}}}")
        
        result = graph_app.invoke(inputs)
        
        generation_data = result.get("generation", {})
        
        reply_text = generation_data.get("reply", "No se pudo generar una respuesta.")
        form_data = generation_data.get("formData", {})
        print(f"---[API] Generación recibida del grafo: {reply_text[:80]}...")
        print(f"---[API] Datos de formulario extraídos: {form_data}")

        updated_history_tuples = chat_history_tuples + [("user", request.message), ("assistant", reply_text)]
        history_for_db = [{"role": role, "content": content} for role, content in updated_history_tuples]

        print(f"---[API] Guardando nuevo historial con {len(history_for_db)} turnos en la sesión {session_id}.")
        # Usar .set() con merge=True o .update() si el documento ya existe
        doc_ref.set({"history": history_for_db}, merge=True)
        print("---[API] Historial guardado con éxito.")

        response_data = {
            "reply": reply_text,
            "session_id": session_id,
            "formData": form_data
        }
        print(f"---[API] Enviando respuesta: {response_data}")
        return response_data
    except Exception as e:
        print(f"---[API-CRITICAL-ERROR] Ha ocurrido una excepción no controlada en handle_chat: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")

def _get_google_auth_flow():
    """Crea una instancia de Flow para el flujo de autenticación web."""
    creds_json_str = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if creds_json_str:
        import json
        try:
            # Carga el contenido de la variable de entorno
            client_config = json.loads(creds_json_str)
            # from_client_config espera el diccionario completo, que es el contenido del archivo JSON
            return InstalledAppFlow.from_client_config(client_config, SCOPES)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=500, detail=f"Error al decodificar GOOGLE_CREDENTIALS_JSON: {e}")

    elif os.path.exists(CREDENTIALS_PATH):
        return InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
    else:
        raise HTTPException(
            status_code=500, 
            detail=f"No se encuentra el archivo de credenciales ('{CREDENTIALS_PATH}') ni la variable de entorno 'GOOGLE_CREDENTIALS_JSON'."
        )


@app.get("/api/auth/google")
def auth_google():
    print("---[API] Iniciando flujo de autenticación en /api/auth/google")
    flow = _get_google_auth_flow()
    flow.redirect_uri = f"{BASE_URL}/api/oauth2callback"
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'  # Fuerza a que siempre se pida consentimiento y se obtenga un refresh_token
    )
    print(f"---[API] Redirigiendo al usuario a: {authorization_url}")
    return RedirectResponse(authorization_url)

@app.get("/api/oauth2callback")
def oauth2callback(request: Request):
    print("---[API] Recibido callback en /api/oauth2callback")
    flow = _get_google_auth_flow()
    flow.redirect_uri = f"{BASE_URL}/api/oauth2callback"
    try:
        print("---[API] Intentando obtener el token de autorización.")
        flow.fetch_token(authorization_response=str(request.url))
        creds = flow.credentials
        print("---[API] Token obtenido con éxito.")

        # Guarda el token en un archivo local. Este archivo es para obtener el
        # contenido que luego pondrás en la variable de entorno GOOGLE_TOKEN_JSON.
        print(f"---[API] Guardando credenciales en {TOKEN_PATH}")
        with open(TOKEN_PATH, 'w') as token_file:
            token_file.write(creds.to_json())
        print("---[API] Credenciales guardadas. Autenticación completada.")
        return {"message": "Autenticación completada con éxito. Ya puedes cerrar esta ventana."}
    except Exception as e:
        print(f"---[API-ERROR] Error en el callback de autenticación: {e}")
        raise HTTPException(status_code=500, detail=f"Error en la autenticación: {e}")

# --- 5. Ejecución para Desarrollo Local ---
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)