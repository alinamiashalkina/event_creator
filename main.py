from fastapi import FastAPI
from sqladmin import Admin

from admin.views import (
    BlacklistedTokenAdmin,
    UserAdmin,
    ContractorAdmin,
    ContractorServiceAdmin,
    PortfolioItemAdmin,
    ReviewAdmin,
    CategoryAdmin,
    ServiceAdmin, EventAdmin, EventInvitationAdmin,
)
from auth.auth import auth_middleware
from auth.routers import router as auth_router
from db.db import engine, get_db_context
from event.routers import router as event_router
from service.routers import router as service_router
from user.routers import router as users_router

app = FastAPI(title="Event Creator")
app.state.get_db_context = get_db_context

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(service_router)
app.include_router(event_router)

app.middleware("http")(auth_middleware)


admin = Admin(app, engine)

admin.add_view(BlacklistedTokenAdmin)
admin.add_view(UserAdmin)
admin.add_view(ContractorAdmin)
admin.add_view(ContractorServiceAdmin)
admin.add_view(PortfolioItemAdmin)
admin.add_view(ReviewAdmin)
admin.add_view(CategoryAdmin)
admin.add_view(ServiceAdmin)
admin.add_view(EventAdmin)
admin.add_view(EventInvitationAdmin)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
