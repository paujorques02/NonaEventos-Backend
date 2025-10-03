from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio

app = FastAPI()

# BBDD en memoria: {chat_id: [mensajes]}
db = {}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/prueba")
async def chat(request: Request):
    data = await request.json()
    user_id = data.get("user_id")
    chat_id = data.get("chat_id")
    message = data.get("message")

    # Si no existe el chat en la "BBDD", lo creamos
    if chat_id not in db:
        db[chat_id] = []

    # Guardamos el mensaje
    db[chat_id].append({"role": "user", "content": message})

    # Respuesta del bot
    bot_reply = f"Hola {user_id}, entendí: {message}"
    db[chat_id].append({"role": "bot", "content": bot_reply})
    asyncio.sleep(5)  # Simula tiempo de procesamiento
    return JSONResponse(content={
        "reply": bot_reply,
        "history": db[chat_id]  # devolvemos historial completo
    })

if __name__ == "__main__":
    uvicorn.run("prueba:app", host="0.0.0.0", port=5000, reload=True)