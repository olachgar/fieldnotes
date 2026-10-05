from fastapi import FastAPI

from app.container import container


def create_note_service(user_id: str):
    return container.create_note_service(user_id)


def create_app() -> FastAPI:
    app = container.create_app()
    app.state.note_service_factory = lambda user_id: create_note_service(user_id)
    return app


app = create_app()
