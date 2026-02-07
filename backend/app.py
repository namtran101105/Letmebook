from fastapi import FastAPI
from routes.trip_routes import router as trip_router

app = FastAPI()

app.include_router(trip_router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
