import httpx
import pytest
from mcp import Client, ClientSession
from mcp.client.streamable_http import streamable_http_client

from app import main as app_main
from app.auth import current_mcp_user_id, firebase_auth_service
from app.mcp_server import create_mcp_server
from app.notes import NoteService
from tests.test_api import FakeNotesRepository


@pytest.mark.asyncio
async def test_mcp_note_tools_share_the_service() -> None:
    repository = FakeNotesRepository()
    server = create_mcp_server(lambda user_id: NoteService(repository, user_id))
    context_token = current_mcp_user_id.set("user-a")

    try:
        async with Client(server) as client:
            created = await client.call_tool(
                "create_note",
                {"name": "MCP note", "subject": "Created through MCP"},
            )
            assert not created.is_error
            note_id = created.structured_content["id"]

            fetched = await client.call_tool("get_note", {"note_id": note_id})
            assert fetched.structured_content["subject"] == "Created through MCP"

            updated = await client.call_tool(
                "update_note",
                {"note_id": note_id, "name": "Updated by MCP", "subject": "New content"},
            )
            assert updated.structured_content["name"] == "Updated by MCP"

            current_mcp_user_id.set("user-b")
            async with Client(server) as other_user_client:
                isolated_list = await other_user_client.call_tool("list_notes", {})
                assert isolated_list.structured_content["result"] == []
                inaccessible = await other_user_client.call_tool("get_note", {"note_id": note_id})
                assert inaccessible.is_error
            current_mcp_user_id.set("user-a")

            listed = await client.call_tool("list_notes", {"ids": [note_id]})
            assert listed.structured_content["result"][0]["id"] == note_id

            deleted = await client.call_tool("delete_note", {"note_id": note_id})
            assert deleted.structured_content["deleted"] is True
    finally:
        current_mcp_user_id.reset(context_token)


@pytest.mark.asyncio
async def test_mcp_missing_note_is_returned_as_tool_error() -> None:
    server = create_mcp_server(lambda user_id: NoteService(FakeNotesRepository(), user_id))
    context_token = current_mcp_user_id.set("user-a")
    try:
        async with Client(server) as client:
            result = await client.call_tool("get_note", {"note_id": "missing"})
    finally:
        current_mcp_user_id.reset(context_token)
    assert result.is_error


@pytest.mark.asyncio
async def test_mcp_streamable_http_crud_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(firebase_auth_service, "verify_token", lambda token: "user-a")
    app = app_main.create_app()

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
            headers={"Authorization": "Bearer valid-token"},
        ) as http_client:
            async with streamable_http_client("http://127.0.0.1:8001/mcp", http_client=http_client) as (
                read_stream,
                write_stream,
            ):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()

                    created = await session.call_tool(
                        "create_note",
                        {"name": "HTTP note", "subject": "created via streamable HTTP"},
                    )
                    note_id = created.structured_content["id"]

                    fetched = await session.call_tool("get_note", {"note_id": note_id})
                    assert fetched.structured_content["subject"] == "created via streamable HTTP"

                    updated = await session.call_tool(
                        "update_note",
                        {"note_id": note_id, "name": "Updated over HTTP", "subject": "updated"},
                    )
                    assert updated.structured_content["name"] == "Updated over HTTP"

                    listed = await session.call_tool("list_notes", {"ids": [note_id]})
                    assert listed.structured_content["result"][0]["id"] == note_id

                    deleted = await session.call_tool("delete_note", {"note_id": note_id})
                    assert deleted.structured_content["deleted"] is True


@pytest.mark.asyncio
async def test_mcp_tools_reject_anonymous_calls() -> None:
    server = create_mcp_server(lambda user_id: NoteService(FakeNotesRepository(), user_id))
    async with Client(server) as client:
        result = await client.call_tool("list_notes", {})
    assert result.is_error
