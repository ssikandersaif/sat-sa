from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import initialize_database
from .routers import entities, findings, peers, auth, upload, reports, ai

initialize_database()
app = FastAPI(title='SAT-SA Offline Audit Platform', version='0.1.0')
app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:5173', 'http://127.0.0.1:5173'], allow_credentials=True, allow_methods=['*'], allow_headers=['*'])
app.include_router(entities.router)
app.include_router(findings.router)
app.include_router(peers.router)
app.include_router(auth.router)
app.include_router(upload.router)
app.include_router(reports.router)
app.include_router(ai.router)

@app.get('/api/health')
def health():
    return {'status': 'ok', 'storage': 'sqlite', 'mode': 'offline'}
