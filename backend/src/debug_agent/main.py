from fastapi import FastAPI

from debug_agent.api.routes import router

app = FastAPI(title="Handwriting OCR Debug Agent", version="0.1.0")
app.include_router(router)
