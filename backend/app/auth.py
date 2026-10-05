from contextvars import ContextVar, Token
from typing import Any

import anyio
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth as firebase_auth
from starlette.responses import JSONResponse

from app.firebase import get_firebase_app

current_mcp_user_id: ContextVar[str | None] = ContextVar("current_mcp_user_id", default=None)
bearer_scheme = HTTPBearer(auto_error=False)


class InvalidAuthToken(ValueError):
    pass


class FirebaseAuthService:
    def verify_token(self, token: str) -> str:
        try:
            decoded: dict[str, Any] = firebase_auth.verify_id_token(
                token,
                app=get_firebase_app(),
                check_revoked=True,
            )
        except Exception as error:
            raise InvalidAuthToken("Invalid Firebase ID token") from error

        user_id = decoded.get("uid")
        if not isinstance(user_id, str) or not user_id:
            raise InvalidAuthToken("Firebase ID token has no user ID")
        return user_id

    def authenticate_user(
        self,
        credentials: HTTPAuthorizationCredentials | None,
    ) -> str:
        if credentials is None or credentials.scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        try:
            return self.verify_token(credentials.credentials)
        except InvalidAuthToken as error:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired Firebase ID token",
                headers={"WWW-Authenticate": "Bearer"},
            ) from error


firebase_auth_service = FirebaseAuthService()


def verify_firebase_id_token(token: str) -> str:
    return firebase_auth_service.verify_token(token)


def require_authenticated_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    return firebase_auth_service.authenticate_user(credentials)


class FirebaseMCPAuthMiddleware:
    def __init__(self, app: Any, auth_service: FirebaseAuthService | None = None) -> None:
        self.app = app
        self.auth_service = auth_service or firebase_auth_service

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        authorization = next(
            (value for key, value in scope["headers"] if key.lower() == b"authorization"),
            b"",
        )
        scheme, separator, raw_token = authorization.partition(b" ")
        if not separator or scheme.lower() != b"bearer" or not raw_token:
            await self._reject(scope, receive, send)
            return

        try:
            user_id = await anyio.to_thread.run_sync(
                self.auth_service.verify_token,
                raw_token.decode("ascii"),
            )
        except (UnicodeDecodeError, InvalidAuthToken):
            await self._reject(scope, receive, send)
            return

        context_token: Token[str | None] = current_mcp_user_id.set(user_id)
        try:
            await self.app(scope, receive, send)
        finally:
            current_mcp_user_id.reset(context_token)

    @staticmethod
    async def _reject(scope: dict[str, Any], receive: Any, send: Any) -> None:
        response = JSONResponse(
            {"detail": "A valid Firebase bearer token is required"},
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Bearer"},
        )
        await response(scope, receive, send)
