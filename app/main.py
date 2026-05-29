from fastapi import FastAPI

app = FastAPI()


@app.get("/healthz")
def get_healthz():
    return {"status": "ok"}
