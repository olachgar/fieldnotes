from datetime import datetime

from firebase_admin import firestore
from google.cloud.firestore import Client

from app.config import get_settings
from app.firebase import create_firestore_client
from app.models import Note, NoteCreate, NoteUpdate
from app.notes import NoteService


class FirestoreNotesRepository:
    def __init__(self, client: Client, collection_name: str = "notes") -> None:
        self.collection = client.collection(collection_name)

    @staticmethod
    def _to_note(document: object) -> Note:
        data = document.to_dict()  # type: ignore[attr-defined]
        if not data:
            raise ValueError("Firestore returned an empty note document")
        date = data.get("date")
        if not isinstance(date, datetime):
            raise ValueError("Firestore note is missing its date timestamp")
        return Note(
            id=document.id,  # type: ignore[attr-defined]
            name=data["name"],
            date=date,
            subject=data["subject"],
        )

    def list_notes(self, owner_id: str, ids: list[str] | None = None) -> list[Note]:
        if ids is None:
            documents = self.collection.where("ownerId", "==", owner_id).stream()
            notes = [self._to_note(document) for document in documents]
            return sorted(notes, key=lambda note: note.date, reverse=True)

        unique_ids = dict.fromkeys(ids)
        notes = []
        for note_id in unique_ids:
            snapshot = self.collection.document(note_id).get()
            data = snapshot.to_dict() if snapshot.exists else None
            if data and data.get("ownerId") == owner_id:
                notes.append(self._to_note(snapshot))
        return sorted(notes, key=lambda note: note.date, reverse=True)

    def get_note(self, owner_id: str, note_id: str) -> Note | None:
        snapshot = self.collection.document(note_id).get()
        data = snapshot.to_dict() if snapshot.exists else None
        return self._to_note(snapshot) if data and data.get("ownerId") == owner_id else None

    def create_note(self, owner_id: str, note: NoteCreate) -> Note:
        reference = self.collection.document()
        reference.set(
            {
                "ownerId": owner_id,
                "name": note.name,
                "subject": note.subject,
                "date": firestore.SERVER_TIMESTAMP,
            }
        )
        return self._to_note(reference.get())

    def update_note(self, owner_id: str, note_id: str, note: NoteUpdate) -> Note | None:
        reference = self.collection.document(note_id)
        snapshot = reference.get()
        data = snapshot.to_dict() if snapshot.exists else None
        if not data or data.get("ownerId") != owner_id:
            return None
        reference.update({"name": note.name, "subject": note.subject})
        return self._to_note(reference.get())

    def delete_note(self, owner_id: str, note_id: str) -> bool:
        reference = self.collection.document(note_id)
        snapshot = reference.get()
        data = snapshot.to_dict() if snapshot.exists else None
        if not data or data.get("ownerId") != owner_id:
            return False
        reference.delete()
        return True


def create_note_service(owner_id: str) -> NoteService:
    settings = get_settings()
    repository = FirestoreNotesRepository(
        create_firestore_client(),
        collection_name=settings.firestore_collection,
    )
    return NoteService(repository, owner_id)
