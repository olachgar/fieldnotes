from typing import Protocol

from app.models import Note, NoteCreate, NoteUpdate


class NoteNotFoundError(LookupError):
    def __init__(self, note_id: str) -> None:
        super().__init__(f"Note '{note_id}' was not found")
        self.note_id = note_id


class NotesRepository(Protocol):
    def list_notes(self, owner_id: str, ids: list[str] | None = None) -> list[Note]: ...

    def get_note(self, owner_id: str, note_id: str) -> Note | None: ...

    def create_note(self, owner_id: str, note: NoteCreate) -> Note: ...

    def update_note(self, owner_id: str, note_id: str, note: NoteUpdate) -> Note | None: ...

    def delete_note(self, owner_id: str, note_id: str) -> bool: ...


class NoteService:
    def __init__(self, repository: NotesRepository, owner_id: str) -> None:
        self.repository = repository
        self.owner_id = owner_id

    def list_notes(self, ids: list[str] | None = None) -> list[Note]:
        return self.repository.list_notes(self.owner_id, ids)

    def get_note(self, note_id: str) -> Note:
        note = self.repository.get_note(self.owner_id, note_id)
        if note is None:
            raise NoteNotFoundError(note_id)
        return note

    def create_note(self, payload: NoteCreate) -> Note:
        return self.repository.create_note(self.owner_id, payload)

    def update_note(self, note_id: str, payload: NoteUpdate) -> Note:
        note = self.repository.update_note(self.owner_id, note_id, payload)
        if note is None:
            raise NoteNotFoundError(note_id)
        return note

    def delete_note(self, note_id: str) -> None:
        if not self.repository.delete_note(self.owner_id, note_id):
            raise NoteNotFoundError(note_id)
