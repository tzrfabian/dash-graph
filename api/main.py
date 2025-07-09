from fastapi import FastAPI
from fastapi.middleware.wsgi import WSGIMiddleware
from .graph import app_dash, router as graph_router

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello, World!"}

app.include_router(graph_router, prefix="/graph", tags=["graph"])

app.mount('/dash-layout', WSGIMiddleware(app_dash.server))