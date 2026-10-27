"""Groups blueprint — creation, membership, hierarchy binding."""

from __future__ import annotations

import uuid

from flask import Blueprint

from app.errors.exceptions import ForbiddenError
from app.extensions import db
from app.middleware.auth import ensure_authenticated
from app.schemas.group_schema import AddMemberSchema, CreateGroupSchema
from app.services.group_service import group_service
from app.utils.responses import success_response
from app.utils.validation import get_json_body, load_schema

bp = Blueprint("groups", __name__, url_prefix="/api/v1/groups")


@bp.post("")
def create_group():
    """Create a group; creator becomes owner + room participant."""
    user_id = uuid.UUID(ensure_authenticated())
    body = load_schema(CreateGroupSchema(), get_json_body())
    group = group_service.create_group(owner_id=user_id, **body)
    return success_response(
        data={"id": str(group.id), "name": group.name, "group_type": group.group_type},
        status_code=201,
        message="Group created.",
    )


@bp.get("")
def my_groups():
    user_id = uuid.UUID(ensure_authenticated())
    groups = group_service.list_for_user(user_id)
    return success_response(
        data={
            "items": [
                {"id": str(g.id), "name": g.name, "group_type": g.group_type} for g in groups
            ]
        },
        message="Your groups listed.",
    )


@bp.get("/<uuid:group_id>")
def get_group(group_id: uuid.UUID):
    user_id = uuid.UUID(ensure_authenticated())
    group = group_service.get_active_group(group_id)
    group_service.assert_membership(group_id, user_id)
    return success_response(
        data={
            "id": str(group.id),
            "name": group.name,
            "description": group.description,
            "group_type": group.group_type,
            "subject_id": str(group.subject_id) if group.subject_id else None,
        },
        message="Group loaded.",
    )


@bp.post("/<uuid:group_id>/members")
def add_member(group_id: uuid.UUID):
    """Invite a user (owner-only; both group + room membership updated)."""
    actor_id = uuid.UUID(ensure_authenticated())
    group = group_service.get_active_group(group_id)
    if group.owner_id != actor_id:
        raise ForbiddenError("Only the group owner can invite members.")

    body = load_schema(AddMemberSchema(), get_json_body())
    member_id = body["user_id"]
    group_service.groups.add_member(group_id, member_id, added_by=actor_id)
    conversation = group_service.conversations.get_by_group(group_id)
    if conversation is not None:
        group_service.conversations.add_participant(conversation.id, member_id)
    db.session.commit()
    return success_response(message="Member added.")
