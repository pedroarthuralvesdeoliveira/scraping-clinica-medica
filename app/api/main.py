from fastapi import FastAPI
from .routes import appointments
import uvicorn


app = FastAPI(title="Bot API")
app.include_router(appointments.router)  

if __name__ == "__main__":
    print("Iniciando API de automação em http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)