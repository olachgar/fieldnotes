# Fieldnotes

A local-first notes app with a SvelteKit interface, a FastAPI REST API, a Streamable HTTP MCP server, and Cloud Firestore storage.

Each note has a Firestore-generated `id`, a short `name`, a server-assigned creation `date`, and a `subject` containing the note text. REST routes and MCP tools share the same owner-scoped backend service.

## Firebase setup

1. Create a Cloud Firestore database in the Firebase project `notes-mcp-a778168` using Native mode.
2. In Firebase Console, enable **Authentication → Sign-in method → Email/Password**.
3. Give the backend service account the Cloud Datastore User role on the project.
4. Keep the service-account JSON outside this repository. For local development, store it at `~/.config/fieldnotes/ServiceAccountKey.json` with owner-only access and set `GOOGLE_APPLICATION_CREDENTIALS` in the root `.env` to that absolute path. Alternatively, configure Google Application Default Credentials.
5. Copy `frontend/.env.example` to `frontend/.env` and set `VITE_FIREBASE_API_KEY` to the Firebase web app API key. The web config is public client configuration; the Admin service-account JSON is a private backend credential.

The SvelteKit UI signs users up with email and password, then sends Firebase ID tokens to REST and MCP. Notes are stored with an `ownerId` and each user can access only their own notes. Firestore Admin SDK calls are authorized by Google credentials and IAM, not Firestore security rules; per-user enforcement happens in the shared backend service. Existing documents without `ownerId` are intentionally inaccessible to signed-in users until you migrate or remove them.

## Run locally

Install Python 3.11 or newer, Node.js 20.19 or newer, npm, and [uv](https://docs.astral.sh/uv/).

Start the backend from the repository root:

```sh
cd backend
uv sync --extra dev
uv run uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

Start the UI in a second terminal:

```sh
cd frontend
npm install
npm run dev -- --host 127.0.0.1
```

Open `http://127.0.0.1:5173`. The API is at `http://127.0.0.1:8001`; interactive REST docs are at `/docs`, health status is at `/health`, and MCP Streamable HTTP is at `/mcp`.

## REST API

| Method | Path | Operation |
| --- | --- | --- |
| `GET` | `/api/notes` | List all notes; repeat `ids` to filter by ID |
| `GET` | `/api/notes/{id}` | Get one note |
| `POST` | `/api/notes` | Create a note with `name` and `subject` |
| `PUT` | `/api/notes/{id}` | Replace a note's `name` and `subject` |
| `DELETE` | `/api/notes/{id}` | Delete a note |

The MCP server exposes `list_notes`, `get_note`, `create_note`, `update_note`, and `delete_note` tools at the same service boundary.

Every REST and MCP request requires a Firebase ID bearer token. The MCP endpoint verifies tokens but does not implement OAuth discovery, so MCP clients must be configured with a user's current Firebase ID token; it expires and needs refreshing. Do not publish or share another user's token.

## Deploy to Render

The root `render.yaml` defines a free Python web service and a static SvelteKit site. To deploy:

1. Push this project to a Git provider and create a Blueprint in Render from that repository.
2. During Blueprint setup, provide `VITE_FIREBASE_API_KEY` from the Firebase web app config.
3. In the `fieldnotes-api` service's Environment settings, upload the service-account JSON as a **Secret File** named `ServiceAccountKey.json`. Render mounts it at `/etc/secrets/ServiceAccountKey.json`, which is configured in the Blueprint.
4. In Firebase Authentication settings, add the deployed `fieldnotes-web` `onrender.com` domain to Authorized domains.
5. Confirm the selected Render region is appropriate for your Firestore database location, then redeploy the Blueprint.

The free API service may sleep after inactivity and take about a minute to wake. The MCP server is public but bearer-protected; configure compatible MCP clients to send `Authorization: Bearer <Firebase ID token>`.

## Test

```sh
cd backend
uv run ruff check .
uv run pytest
cd ../frontend
npm run check
npm run build
```

Tests use a fake note repository and do not require Firebase credentials. To test actual Firestore persistence, configure the credentials above or use the Firestore Emulator.

## Security boundary

The local command binds to localhost. A Render web service is internet-reachable; authentication and Firestore owner checks are therefore required. Firebase API keys are public client identifiers, but service-account JSON and local `.env` files must never be committed. Use Firebase email enumeration protection and consider App Check/rate limiting before inviting public signups.
