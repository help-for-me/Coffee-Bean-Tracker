from fastapi import FastAPI

app = FastAPI(title="Coffee Bean Tracker")


@app.get("/health")
def health():
    return {"status": "ok"}
