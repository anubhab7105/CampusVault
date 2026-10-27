"""Room naming + authorization helpers.

Rooms (docs/07_SOCKET_GUIDE.md): group_<group_id>, dm_<conversation_id>.
Authorization: every join requires group membership / DM participation,
validated against the database — room names alone are never trusted.
"""

from __future__ import annotations

import uuid

from flask_socketio import join_room, leave_room

from app.errors.exceptions import ForbiddenError
from app.services.group_service import group_service


def group_room(group_id: uuid.UUID) -> str:
    return f"group_{group_id}"


def dm_room(conversation_id: uuid.UUID) -> str:
    return f"dm_{conversation_id}"


def authorize_group_join(user_id: str, group_id_raw: str) -> uuid.UUID:
    try:
        group_id = uuid.UUID(group_id_raw)
    except (ValueError, AttributeError) as err:
        raise ForbiddenError("Invalid group id.") from err
    group_service.get_active_group(group_id)  # raises NotFoundError
    if not group_service.groups.is_member(group_id, uuid.UUID(user_id)):
        raise ForbiddenError("Group membership required.")
    return group_id


def join_group_room(sid: str, user_id: str, group_id_raw: str) -> str:
    group_id = authorize_group_join(user_id, group_id_raw)
    join_room(group_room(group_id), sid=sid)
    return str(group_id)


def leave_group_room(sid: str, group_id_raw: str) -> None:
    try:
        group_id = uuid.UUID(group_id_raw)
    except (ValueError, AttributeError) as err:
        raise ForbiddenError("Invalid group id.") from err
    leave_room(group_room(group_id), sid=sid)
