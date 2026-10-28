from fastapi import FastAPI

from app.db import Base, engine

app = FastAPI(title="curiosity-feed")

Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    return {"status": "ok"}
