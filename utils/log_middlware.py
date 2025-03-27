import logging
import logging.config
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from utils.logger import logging_config


logging.config.dictConfig(logging_config)
logger = logging.getLogger("fastapi")


async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Обработчик  http-ошибок
    """
    logger.warning(
        f"HTTP Exception {exc.status_code}: {exc.detail} | "
        f"Path: {request.url.path}"
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
):
    """
    Обработчик ошибок валидации
    """
    logger.error(
        f"Validation Error: {exc.errors()} | "
        f"Path: {request.url.path}", exc_info=True
    )
    return JSONResponse(
        status_code=400,
        content={"detail": "Validation error"},
    )


async def global_exception_handler(request: Request, exc: Exception):
    """
    Обработчик ошибок сервера и глобальных ошибок
    """
    logger.critical(
        f"Unhandled Exception: {str(exc)} | "
        f"Path: {request.url.path}", exc_info=True
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
    )


class LogRequestsMiddleware(BaseHTTPMiddleware):
    """
    Middlware для логирования всех запросов на старте
    """
    async def dispatch(self, request: Request, call_next):
        logger.info(f"{request.method} Path: {request.url.path}")
        response = await call_next(request)
        if response.status_code < 400:
            logger.info(
                f"Response Status: {response.status_code} | "
                f"Path: {request.url.path}"
            )
        return response
