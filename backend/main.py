import os, sys

current_dir = os.path.dirname(os.path.abspath(__file__))
backend_root = os.path.abspath(os.path.join(current_dir, ".."))
if backend_root not in sys.path:
    sys.path.append(backend_root)
current_dir = os.path.dirname(os.path.abspath(__file__))        
repo_root   = os.path.abspath(os.path.join(current_dir, "..")) 
legacy_path = os.path.join(current_dir, "legacy")

for path in (repo_root, legacy_path):
    if path not in sys.path:
        sys.path.insert(0, path)
    
current_dir = os.path.dirname(os.path.abspath(__file__))        
repo_root   = os.path.abspath(os.path.join(current_dir, "..")) 
legacy_path = os.path.join(current_dir, "tools")

for path in (repo_root, legacy_path):
    if path not in sys.path:
        sys.path.insert(0, path)

from fastapi import FastAPI


from backend.routers import query, interview

app = FastAPI(title="Pharma RAG API", version="1.0.0")

app.include_router(query.router)
app.include_router(interview.router)

@app.get("/health")
def health():
    return {"status": "ok"}