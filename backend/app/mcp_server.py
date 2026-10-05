from collections.abc import Callable
from typing import Any

from mcp.server import MCPServer

from app.auth import current_mcp_user_id
from app.firestore_repository import create_note_service
from app.models import Note, NoteCreate, NoteUpdate
from app.notes import NoteService

ServiceProvider = Callable[[str], NoteService]


def _note_data(note: Note) -> dict[str, Any]:
    return note.model_dump(mode="json")


def _service_for_current_user(service_provider: ServiceProvider) -> NoteService:
    user_id = current_mcp_user_id.get()
    if user_id is None:
        raise PermissionError("A Firebase-authenticated user is required")
    return service_provider(user_id)


def create_mcp_server(service_provider: ServiceProvider = create_note_service) -> MCPServer:
    server = MCPServer("Firebase Notes")

    @server.tool()
    def list_notes(ids: list[str] | None = None) -> list[dict[str, Any]]:
        """List all notes, or only notes whose document IDs are provided."""
        service = _service_for_current_user(service_provider)
        return [_note_data(note) for note in service.list_notes(ids)]

    @server.tool()
    def get_note(note_id: str) -> dict[str, Any]:
        """Get one note by its Firestore document ID."""
        return _note_data(_service_for_current_user(service_provider).get_note(note_id))

    @server.tool()
    def create_note(name: str, subject: str) -> dict[str, Any]:
        """Create a note. Name is its label and subject is its content."""
        service = _service_for_current_user(service_provider)
        return _note_data(service.create_note(NoteCreate(name=name, subject=subject)))

    @server.tool()
    def update_note(note_id: str, name: str, subject: str) -> dict[str, Any]:
        """Replace the label and content of an existing note."""
        payload = NoteUpdate(name=name, subject=subject)
        service = _service_for_current_user(service_provider)
        return _note_data(service.update_note(note_id, payload))

    @server.tool()
    def delete_note(note_id: str) -> dict[str, str | bool]:
        """Delete an existing note by its Firestore document ID."""
        _service_for_current_user(service_provider).delete_note(note_id)
        return {"id": note_id, "deleted": True}

    return server
