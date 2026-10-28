from fastapi import FastAPI
from routers.transcript_router import router as transcript_router

app = FastAPI()

app.include_router(transcript_router)

@app.get('/')
async def root():
    return {'message' : 'Welcome'}
