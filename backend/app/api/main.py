from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router

app = FastAPI(title="BrainVC API", description="The VC Brain — Hack-Nation 6th Global AI Hackathon")

# Local-only demo: permissive CORS so the Lovable frontend can hit localhost.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")
