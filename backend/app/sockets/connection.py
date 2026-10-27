"""Connection lifecycle: JWT-authenticated handshake + disconnect cleanup."""

from __future__ import annotations

import logging

from flask import current_app, request
from flask_socketio import disconnect, emit

from app.extensions import socketio
from app.services.connections import (
    register_connection,
    unregister_connection,
)

logger = logging.getLogger("campusvault.socket")


@socketio.on("connect")
def on_connect(auth) -> bool:  # type: ignore[valid-type]
    """JWT must ride the handshake payload — no anonymous sockets, ever."""
    token = None
    if isinstance(auth, dict):
        token = auth.get("token")
    if not token:
        header = request.headers.get("Authorization", "")
        if header.startswith("Bearer "):
            token = header.removeprefix("Bearer ")

    user_id = _verify_handshake_token(token)
    if user_id is None:
        logger.warning("socket_rejected ip=%s", request.remote_addr)
        return False  # Engine.IO refuses the connection

    register_connection(user_id, request.sid)
    emit(
        "connection_ack",
        {"success": True, "message": "Connected.", "data": {"user_id": user_id}},
    )
    return True


def _verify_handshake_token(token: str | None) -> str | None:
    if not token:
        return None
    try:
        from flask_jwt_extended import decode_token

        payload = decode_token(token)
        if payload.get("type") != "access":
            return None
        user_id = payload.get("sub")
        if not user_id:
            return None
        import uuid as uuid_mod

        uuid_mod.UUID(str(user_id))
        return str(user_id)
    except Exception as err:  # noqa: BLE001 — any token failure denies access
        current_app.logger.warning("socket_auth_failed %s", type(err).__name__)
        return None


@socketio.on("disconnect")
def on_disconnect() -> None:
    from app.services.connections import user_id_for_session

    user_id = user_id_for_session(request.sid)
    unregister_connection(request.sid)
    if user_id:
        logger.info("socket_disconnected user=%s", user_id)
