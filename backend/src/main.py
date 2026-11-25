import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config.settings import Settings
from .database.db import Database
from .database.seed import seed
from .modules.appointments.repository import AppointmentRepository
from .modules.appointments.service import AppointmentService
from .modules.appointments.router import router
from .modules.voice_agent.router import router as voice_router


def create_app(settings: Settings | None = None):
    settings = settings or Settings()
    db = Database(settings.database_path)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await asyncio.to_thread(db.initialize)
        await asyncio.to_thread(seed, db)
        app.state.appointments = AppointmentService(AppointmentRepository(db))
        app.state.settings = settings
        app.state.voice_handler = None
        try:
            yield
        finally:
            if app.state.voice_handler is not None:
                await app.state.voice_handler.close()

    app = FastAPI(title='Hospital Appointment Agent', lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_origin], allow_methods=['GET', 'POST', 'PATCH'], allow_headers=['Content-Type'])
    app.include_router(router)
    app.include_router(voice_router)

    @app.get('/api/health')
    async def health():
        return {'status': 'ok', 'voice': 'configured' if settings.voice_configured else 'missing_credentials'}

    return app


app = create_app()
