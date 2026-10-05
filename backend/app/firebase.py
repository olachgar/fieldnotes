from functools import lru_cache

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore import Client

from app.config import get_settings


@lru_cache
def get_firebase_app() -> firebase_admin.App:
    settings = get_settings()
    try:
        return firebase_admin.get_app()
    except ValueError:
        credential = (
            credentials.Certificate(settings.google_application_credentials)
            if settings.google_application_credentials
            else credentials.ApplicationDefault()
        )
        return firebase_admin.initialize_app(
            credential,
            {"projectId": settings.firebase_project_id},
        )


def create_firestore_client() -> Client:
    return firestore.client(app=get_firebase_app())
