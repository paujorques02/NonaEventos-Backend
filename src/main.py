from flask import Flask, request, jsonify
from firestore.conversation_store import store_conversation, retrieve_conversation
from gemini.llm_client import GeminiLLM
from embeddings.embeddings_manager import create_embeddings
from services.services_info import get_services_info, rag_query
from calendar.google_calendar import get_events, calendar_query

# LangGraph imports
from langgraph import Agent, Tool, Flow

app = Flask(__name__)

# Tool 1: RAG (servicios/precios)
def rag_tool(query):
    return rag_query(query)  # Implementa rag_query en services_info.py

# Tool 2: Google Calendar
def calendar_tool(query):
    return calendar_query(query)  # Implementa calendar_query en google_calendar.py

# Tool 3: Respuesta amable por defecto
def fallback_tool(query):
    return "Lo siento, no puedo ayudarte con eso, pero puedo responder sobre servicios o disponibilidad."

tools = [
    Tool(name="RAG", func=rag_tool, description="Información sobre servicios y precios"),
    Tool(name="Calendar", func=calendar_tool, description="Consultar disponibilidad en Google Calendar"),
    Tool(name="Fallback", func=fallback_tool, description="Respuesta amable si no se puede ayudar"),
]

llm = GeminiLLM()  # Implementa GeminiLLM en llm_client.py
agent = Agent(llm=llm, tools=tools)
flow = Flow(agent=agent)

@app.route('/chat', methods=['POST'])
def chat():
    user_input = request.json.get('message')
    conversation_id = request.json.get('conversation_id')

    # Recuperar la conversación previa
    previous_conversation = retrieve_conversation(conversation_id)

    # Ejecutar el flujo agentico
    response = flow.run(user_input)

    # Guardar la conversación
    store_conversation(conversation_id, user_input)
    store_conversation(conversation_id, response)

    # Crear embeddings para la conversación actualizada
    conversation = previous_conversation + [user_input, response]
    embeddings = create_embeddings(conversation)

    return jsonify({
        'response': response,
        'embeddings': embeddings
    })

@app.route('/events', methods=['GET'])
def events():
    events = get_events()
    return jsonify(events)

@app.route('/services', methods=['GET'])
def services():
    services_info = get_services_info()
    return jsonify(services_info)

@app.route('/prueba', methods=['POST'])
def prueba():
    user_input = request.json.get('message')
    return jsonify({'message': 'Prueba exitosa. Este es tu mensaje: ' + user_input})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)