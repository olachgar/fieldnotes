from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.auth import require_authenticated_user
from app.main import app
from app.models import Note, NoteCreate, NoteUpdate
from app.notes import NoteService


class FakeNotesRepository:
    def __init__(self) -> None:
        self.notes: dict[tuple[str, str], Note] = {}
        self.next_id = 1

    def list_notes(self, owner_id: str, ids: list[str] | None = None) -> list[Note]:
        notes = [note for (note_owner, _), note in self.notes.items() if note_owner == owner_id]
        if ids is not None:
            notes = [note for note in notes if note.id in ids]
        return sorted(notes, key=lambda note: note.date, reverse=True)

    def get_note(self, owner_id: str, note_id: str) -> Note | None:
        return self.notes.get((owner_id, note_id))

    def create_note(self, owner_id: str, note: NoteCreate) -> Note:
        created = Note(
            id=str(self.next_id),
            name=note.name,
            subject=note.subject,
            date=datetime.now(UTC),
        )
        self.next_id += 1
        self.notes[(owner_id, created.id)] = created
        return created

    def update_note(self, owner_id: str, note_id: str, note: NoteUpdate) -> Note | None:
        existing = self.notes.get((owner_id, note_id))
        if existing is None:
            return None
        updated = existing.model_copy(update={"name": note.name, "subject": note.subject})
        self.notes[(owner_id, note_id)] = updated
        return updated

    def delete_note(self, owner_id: str, note_id: str) -> bool:
        return self.notes.pop((owner_id, note_id), None) is not None


@pytest.fixture(scope="module")
def api_client():
    repository = FakeNotesRepository()
    owner_id = ["user-a"]
    original_factory = main_module.create_note_service

    def user_override() -> str:
        return owner_id[0]

    main_module.create_note_service = lambda user_id: NoteService(repository, user_id)
    app.dependency_overrides[require_authenticated_user] = user_override
    try:
        with TestClient(app) as client:
            yield client, owner_id
    finally:
        main_module.create_note_service = original_factory
        app.dependency_overrides.clear()


def test_rest_crud_and_owner_isolation(api_client) -> None:
    client, owner_id = api_client
    created_response = client.post(
        "/api/notes",
        json={"name": "First note", "subject": "Original text"},
    )
    assert created_response.status_code == 201
    created = created_response.json()
    assert created["id"] == "1"
    original_date = created["date"]

    owner_id[0] = "user-b"
    assert client.get("/api/notes").json() == []
    assert client.get("/api/notes/1").status_code == 404
    assert client.put(
        "/api/notes/1",
        json={"name": "Unauthorized edit", "subject": "Not mine"},
    ).status_code == 404
    assert client.delete("/api/notes/1").status_code == 404

    owner_id[0] = "user-a"
    updated_response = client.put(
        "/api/notes/1",
        json={"name": "Updated note", "subject": "Revised text"},
    )
    assert updated_response.status_code == 200
    assert updated_response.json()["date"] == original_date

    listed = client.get("/api/notes", params={"ids": ["1", "missing"]})
    assert listed.status_code == 200
    assert [note["id"] for note in listed.json()] == ["1"]

    assert client.get("/api/notes/missing").status_code == 404
    assert client.delete("/api/notes/1").status_code == 204
    assert client.delete("/api/notes/1").status_code == 404


def test_create_rejects_blank_note_fields(api_client: TestClient) -> None:
    client, _ = api_client
    response = client.post("/api/notes", json={"name": "  ", "subject": "Body"})
    assert response.status_code == 422


def test_rest_and_mcp_reject_requests_without_bearer_auth(api_client) -> None:
    client, _ = api_client
    user_override = app.dependency_overrides.pop(require_authenticated_user)
    try:
        assert client.get("/api/notes").status_code == 401
        assert client.get("/mcp").status_code == 401
    finally:
        app.dependency_overrides[require_authenticated_user] = user_override
