import os
import json
from typing import List, Dict, Any, TypedDict, Optional, Sequence

from langchain_community.document_loaders import UnstructuredMarkdownLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END

from api.services.calendar import get_calendar_events

# Global variables for the RAG retriever
vectorstore = None
retriever = None

@tool
def search_event_info(query: str) -> str:
    """Searches for information about NonaEventos services, prices, and event details."""
    print(f"---[TOOL] Executing search_event_info with query: {query}")
    if retriever:
        relevant_docs = retriever.get_relevant_documents(query)
        if relevant_docs:
            context = "\n\n".join(doc.page_content for doc in relevant_docs)
            print(f"---[TOOL] RAG context found: {context[:200]}...")
            return f"Relevant information found:\n{context}"
    return "No relevant information found."

tools = [get_calendar_events, search_event_info]

class AgentState(TypedDict):
    question: str
    chat_history: Sequence[tuple]
    generation: Any
    tool_calls: List[Dict[str, Any]]
    tool_output: Optional[Dict[str, Any]]

def should_call_tools(state: AgentState) -> str:
    """Determines whether the agent should call a tool."""
    print("\n---[GRAPH] Node: should_call_tools ---")
    if state.get("tool_calls"):
        print("---[GRAPH] Decision: YES, tools needed. -> Redirecting to 'tools'")
        return "tools"
    else:
        print("---[GRAPH] Decision: NO, tools not needed. -> Redirecting to 'responder'")
        return "responder"

def call_model(state: AgentState):
    print("\n---[GRAPH] Node: agent (call_model) ---")
    print(f"---[GRAPH] User question: {state['question']}")
    
    chat_history = state.get('chat_history', [])
    
    messages = [("system", "You are a virtual assistant for NonaEventos. Respond to user questions in a friendly and helpful manner. You can use the available tools to get information.")]
    messages.extend(chat_history)
    messages.append(("user", state['question']))
    
    llm = ChatGoogleGenerativeAI(model="models/gemini-pro-latest", temperature=0).bind_tools(tools)
    response = llm.invoke(messages)
    print(f"---[GRAPH] Model response (with tool_calls): {response.tool_calls}")
    return {"tool_calls": response.tool_calls}

def call_tools(state: AgentState):
    print("\n---[GRAPH] Node: tools (call_tools) ---")
    tool_map = {tool.name: tool for tool in tools}
    output = {}
    for call in state["tool_calls"]:
        tool_name = call["name"]
        tool_args = call["args"]
        print(f"---[GRAPH] Executing tool: '{tool_name}' with args: {tool_args}")
        if tool_name in tool_map:
            try:
                output[tool_name] = tool_map[tool_name].invoke(tool_args)
                print(f"---[GRAPH] Result of '{tool_name}': {output[tool_name]}")
            except Exception as e:
                output[tool_name] = f"Error executing tool {tool_name}: {e}"
    return {"tool_output": output}

def generate_final_answer(state: AgentState):
    print("---GENERATING FINAL ANSWER AND EXTRACTING DATA---")
    question = state['question']
    chat_history = state['chat_history']
    tool_output_dict = state.get('tool_output')

    if tool_output_dict:
        tool_output_str = "\n".join(f"- {tool}: {output}" for tool, output in tool_output_dict.items())
    else:
        tool_output_str = "No tools were used in this turn."

    system_prompt = """You are a virtual assistant for NonaEventos. Your goal is twofold:
1.  **Converse politely**: Answer the user's question based on the history and the output of the tools.
2.  **Extract data**: Fill out a form with the information provided by the user.

**Data extraction instructions:**
-   `name`: The user's full name.
-   `email`: The user's email address.
-   `phone`: The user's phone number.
-   `eventType`: The type of event. Must be one of: "Wedding", "Birthday / Social", "Corporate", "Other".
-   `message`: A concise summary of the user's request in 1-2 short sentences.

**Required Output Format:**
Your final answer MUST be a valid JSON code block. The JSON object must have two keys:
1.  `reply`: (string) Your conversational response to the user.
2.  `formData`: (JSON object) An object with the fields you have extracted. If a field is not yet known, do not include it or leave it as null.
"""

    messages = [("system", system_prompt)]
    
    if chat_history:
        messages.extend(chat_history)
        
    if tool_output_dict:
        tool_output_message = f"Tools used:\n{tool_output_str}"
        messages.append(("system", tool_output_message))

    messages.append(("user", question))
    
    messages.append(("system", "**Your Answer (only the JSON code block):**"))

    llm = ChatGoogleGenerativeAI(model="models/gemini-pro-latest", temperature=0.1)
    
    response = llm.invoke(messages)
    raw_response = response.content if response.content else ""

    safe_raw_response = raw_response.encode('utf-8', 'ignore').decode('utf-8')
    print(f"---[GRAPH] RAW model response: {safe_raw_response}")

    try:
        json_block = raw_response.strip().replace("```json", "").replace("```", "").strip()
        if not json_block:
            return {"generation": {"reply": "I could not process your request. Could you try again?", "formData": {}}}
        parsed_json = json.loads(json_block)
        print("---[GRAPH] JSON parsed successfully.")
        return {"generation": parsed_json}
    except Exception as e:
        print(f"---[GRAPH-ERROR] Could not parse JSON from AI response: {e}")
        return {"generation": {"reply": raw_response, "formData": {}}}

def setup_retriever():
    global vectorstore, retriever
    doc_path = os.path.join(os.path.dirname(__file__), '..', '..', 'docs', 'info_eventos.md')
    if not os.path.exists(doc_path):
        raise FileNotFoundError(f"Knowledge file not found at: {doc_path}")
    loader = UnstructuredMarkdownLoader(doc_path)
    docs = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splits = text_splitter.split_documents(docs)
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    vectorstore = FAISS.from_documents(splits, embeddings)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
    print("Retriever configured and ready.")

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
