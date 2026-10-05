from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status

from app.auth import require_authenticated_user
from app.models import Note, NoteCreate, NoteUpdate
from app.notes import NoteNotFoundError, NoteService


def get_note_service(
    request: Request,
    user_id: str = Depends(require_authenticated_user),
) -> NoteService:
    factory: Callable[[str], NoteService] | None = getattr(
        request.app.state,
        "note_service_factory",
        None,
    )
    if factory is not None:
        return factory(user_id)

    from app import main as main_module

    return main_module.create_note_service(user_id)


def create_rest_app() -> FastAPI:
    app = FastAPI(title="Firebase Notes API", version="0.1.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/notes", response_model=list[Note])
    def list_notes(
        ids: Annotated[list[str] | None, Query()] = None,
        service: Annotated[NoteService, Depends(get_note_service)] = None,
    ) -> list[Note]:
        assert service is not None
        return service.list_notes(ids)

    @app.get("/api/notes/{note_id}", response_model=Note)
    def get_note(
        note_id: str,
        service: Annotated[NoteService, Depends(get_note_service)],
    ) -> Note:
        try:
            return service.get_note(note_id)
        except NoteNotFoundError as error:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error

    @app.post("/api/notes", response_model=Note, status_code=status.HTTP_201_CREATED)
    def create_note(
        payload: NoteCreate,
        service: Annotated[NoteService, Depends(get_note_service)],
    ) -> Note:
        return service.create_note(payload)

    @app.put("/api/notes/{note_id}", response_model=Note)
    def update_note(
        note_id: str,
        payload: NoteUpdate,
        service: Annotated[NoteService, Depends(get_note_service)],
    ) -> Note:
        try:
            return service.update_note(note_id, payload)
        except NoteNotFoundError as error:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error

    @app.delete("/api/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_note(
        note_id: str,
        service: Annotated[NoteService, Depends(get_note_service)],
    ) -> Response:
        try:
            service.delete_note(note_id)
        except NoteNotFoundError as error:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return app
