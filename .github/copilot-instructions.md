# Project instructions

- The backend is a FastAPI application that serves REST routes and the official MCP Python SDK over Streamable HTTP at `/mcp`.
- REST and MCP operations must use the shared `NoteService`; Firestore persistence belongs in the repository layer.
- Firebase Admin credentials are local environment configuration. Never add service-account keys or Firebase credentials to source control.
- Notes contain `id`, `name`, immutable creation `date`, and `subject` content. Firestore generates IDs and server timestamps.
- MCP SDK documentation: https://py.sdk.modelcontextprotocol.io/
- MCP ASGI integration and lifespan guidance: https://py.sdk.modelcontextprotocol.io/run/asgi/
