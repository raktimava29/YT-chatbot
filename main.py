import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from core.errors import DependencyUnavailableError
from core.logging_config import configure_logging

from routers.transcript_router import router as transcript_router
from routers.chat_router import router as chat_router

configure_logging()

logger = logging.getLogger(__name__)

app = FastAPI()


app.include_router(transcript_router)
app.include_router(chat_router)


@app.exception_handler(DependencyUnavailableError)
async def dependency_error_handler(
    request: Request,
    exc: DependencyUnavailableError,
):
    logger.error(
        "Dependency failure on %s %s: %s",
        request.method,
        request.url.path,
        exc,
    )

    return JSONResponse(
        status_code=503,
        content={
            "detail": "Required service temporarily unavailable."
        },
    )


@app.exception_handler(Exception)
async def unexpected_error_handler(
    request: Request,
    exc: Exception,
):
    logger.exception(
        "Unhandled error on %s %s",
        request.method,
        request.url.path,
    )

    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error."
        },
    )


@app.get("/")
async def root():
    return {"message": "Welcome"}