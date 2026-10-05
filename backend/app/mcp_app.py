from fastapi import FastAPI
from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

from app.auth import FirebaseMCPAuthMiddleware
from app.config import get_settings
from app.mcp_server import create_mcp_server


def create_mcp_http_app() -> tuple[MCPServer, FastAPI]:
    settings = get_settings()
    server = create_mcp_server()
    transport_settings = (
        TransportSecuritySettings(
            allowed_hosts=[
                settings.render_external_hostname,
                f"{settings.render_external_hostname}:*",
            ],
            allowed_origins=settings.allowed_origins,
        )
        if settings.render_external_hostname
        else None
    )
    http_app = server.streamable_http_app(transport_security=transport_settings)
    return server, FirebaseMCPAuthMiddleware(http_app)
