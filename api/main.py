import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.core.config import ORIGINS
from api.routes import auth, chat
from api.services.agent import setup_retriever

app = FastAPI(docs_url=None, redoc_url=None)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api")
app.include_router(chat.router, prefix="/api")

@app.on_event("startup")
async def startup_event():
    setup_retriever()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
