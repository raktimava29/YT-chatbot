from fastapi import FastAPI
from routers.transcript_router import router as transcript_router
from routers.chat_router import router as chat_router

app = FastAPI()

app.include_router(transcript_router)
app.include_router(chat_router)

@app.get('/')
async def root():
    return {'message' : 'Welcome'}
