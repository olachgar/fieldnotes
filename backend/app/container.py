from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import create_rest_app
from app.config import get_settings
from app.firestore_repository import create_note_service as create_firestore_note_service
from app.mcp_app import create_mcp_http_app
from app.notes import NoteService


@dataclass(slots=True)
class AppContainer:
    note_service_factory: Callable[[str], NoteService] = create_firestore_note_service

    def create_note_service(self, user_id: str) -> NoteService:
        return self.note_service_factory(user_id)

    def create_app(self) -> FastAPI:
        settings = get_settings()
        app = create_rest_app()
        mcp_server, mcp_app = create_mcp_http_app()

        @asynccontextmanager
        async def lifespan(_: FastAPI) -> AsyncIterator[None]:
            async with mcp_server.session_manager.run():
                yield

        app.router.lifespan_context = lifespan
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.allowed_origins,
            allow_methods=["GET", "POST", "PUT", "DELETE"],
            allow_headers=[
                "Authorization",
                "Content-Type",
                "Last-Event-ID",
                "Mcp-Method",
                "Mcp-Name",
                "Mcp-Protocol-Version",
                "Mcp-Session-Id",
            ],
            expose_headers=["Mcp-Session-Id"],
        )
        app.mount("/", mcp_app)
        return app


container = AppContainer()
