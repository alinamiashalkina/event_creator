import uvicorn
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError, HTTPException

from auth.auth import auth_middleware
from auth.routers import router as auth_router
from admin.views import setup_admin
from db.db import get_db_context
from service.routers import router as service_router
from user.routers import router as users_router
from event.routers import router as event_router
from utils.log_middlware import (
    LogRequestsMiddleware,
    http_exception_handler,
    validation_exception_handler,
    global_exception_handler,
)


app = FastAPI(title="Event Creator")
app.state.get_db_context = get_db_context

app.middleware("http")(auth_middleware)
app.add_middleware(LogRequestsMiddleware)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(service_router)
app.include_router(event_router)

setup_admin(app)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
