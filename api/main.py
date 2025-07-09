from fastapi import FastAPI
from fastapi.middleware.wsgi import WSGIMiddleware
from .graph import app_dash

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello, World!"}

app.mount('/dash-layout', WSGIMiddleware(app_dash.server))