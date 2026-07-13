"""
Integration tests for ChatService — real Postgres. Socket.IO handlers
themselves aren't tested here (they're thin wrappers around this exact
service layer, which is the point of the shared-service design in
API_SPEC_CHAT.md) — the business logic they call is what's under test.
"""
import pytest

from app.models.auth import UserType
from app.models.chat import ContentType, GroupType
from app.repositories.auth_repository import AuthRepository
from app.services.chat_service import ChatService
from app.utils.exceptions import ForbiddenError, NotFoundError, ValidationError


def _make_users(db, n=2):
    import uuid
    auth_repo = AuthRepository(db)
    suffix = uuid.uuid4().hex[:8]
    users = [auth_repo.create_user(f"chatuser{i}_{suffix}@college.edu", f"User {i}", UserType.STUDENT) for i in range(n)]
    db.commit()
    return users


class TestDMConversations:
    def test_start_dm_creates_conversation_with_both_participants(self, db):
        service = ChatService(db)
        u1, u2 = _make_users(db)

        result = service.start_dm(u1.id, u2.id)
        assert result["type"] == "dm"
        assert result["created"] is True

        # Both users should now see this conversation in their list.
        convs_u1 = service.list_conversations(u1.id)
        convs_u2 = service.list_conversations(u2.id)
        assert any(c["id"] == result["id"] for c in convs_u1)
        assert any(c["id"] == result["id"] for c in convs_u2)

    def test_start_dm_idempotent(self, db):
        service = ChatService(db)
        u1, u2 = _make_users(db)

        first = service.start_dm(u1.id, u2.id)
        second = service.start_dm(u1.id, u2.id)
        assert first["id"] == second["id"]
        assert second["created"] is False

    def test_start_dm_with_self_rejected(self, db):
        service = ChatService(db)
        u1, _ = _make_users(db)
        with pytest.raises(ValidationError) as exc_info:
            service.start_dm(u1.id, u1.id)
        assert exc_info.value.code == "CANNOT_DM_SELF"

    def test_start_dm_unknown_user_rejected(self, db):
        import uuid
        service = ChatService(db)
        u1, _ = _make_users(db)
        with pytest.raises(NotFoundError) as exc_info:
            service.start_dm(u1.id, uuid.uuid4())
        assert exc_info.value.code == "USER_NOT_FOUND"


class TestMessagesAndAuthorization:
    def test_send_message_and_read_back_in_history(self, db):
        service = ChatService(db)
        u1, u2 = _make_users(db)
        dm = service.start_dm(u1.id, u2.id)

        service.send_message(dm["id"], u1.id, "Hello there", ContentType.TEXT)

        history = service.get_message_history(dm["id"], u2.id, before=None, limit=50)
        assert len(history["items"]) == 1
        assert history["items"][0]["content"] == "Hello there"
        assert history["items"][0]["sender_id"] == u1.id

    def test_non_participant_cannot_read_history(self, db):
        service = ChatService(db)
        u1, u2 = _make_users(db)
        outsider, _ = _make_users(db)
        dm = service.start_dm(u1.id, u2.id)

        with pytest.raises(ForbiddenError) as exc_info:
            service.get_message_history(dm["id"], outsider.id, before=None, limit=50)
        assert exc_info.value.code == "FORBIDDEN"

    def test_non_participant_cannot_send_message(self, db):
        service = ChatService(db)
        u1, u2 = _make_users(db)
        outsider, _ = _make_users(db)
        dm = service.start_dm(u1.id, u2.id)

        with pytest.raises(ForbiddenError):
            service.send_message(dm["id"], outsider.id, "sneaky", ContentType.TEXT)

    def test_edit_message_by_owner_succeeds(self, db):
        service = ChatService(db)
        u1, u2 = _make_users(db)
        dm = service.start_dm(u1.id, u2.id)
        message = service.send_message(dm["id"], u1.id, "original", ContentType.TEXT)

        edited = service.edit_message(message["id"], u1.id, "edited text")
        assert edited["content"] == "edited text"
        assert edited["edited_at"] is not None

    def test_edit_message_by_non_owner_rejected(self, db):
        service = ChatService(db)
        u1, u2 = _make_users(db)
        dm = service.start_dm(u1.id, u2.id)
        message = service.send_message(dm["id"], u1.id, "original", ContentType.TEXT)

        with pytest.raises(ForbiddenError):
            service.edit_message(message["id"], u2.id, "hijacked")

    def test_delete_message_soft_deletes_and_clears_content(self, db):
        service = ChatService(db)
        u1, u2 = _make_users(db)
        dm = service.start_dm(u1.id, u2.id)
        message = service.send_message(dm["id"], u1.id, "to be deleted", ContentType.TEXT)

        deleted = service.delete_message(message["id"], u1.id)
        assert deleted["deleted"] is True
        assert deleted["content"] is None

        # History should still show it, per the API spec's "placeholder in order" rule.
        history = service.get_message_history(dm["id"], u2.id, before=None, limit=50)
        assert history["items"][0]["deleted"] is True
        assert history["items"][0]["content"] is None

    def test_sending_message_updates_conversation_ordering(self, db):
        """Confirms the create_message fix: sending a message should move
        the conversation to the top of the list."""
        service = ChatService(db)
        u1, u2, u3 = _make_users(db, n=3)
        dm_a = service.start_dm(u1.id, u2.id)
        dm_b = service.start_dm(u1.id, u3.id)

        # Message only in dm_b — it should now be first for u1.
        service.send_message(dm_b["id"], u1.id, "hi", ContentType.TEXT)

        conversations = service.list_conversations(u1.id)
        assert conversations[0]["id"] == dm_b["id"]


class TestReceipts:
    def test_mark_read_updates_receipt_counts_and_unread(self, db):
        service = ChatService(db)
        u1, u2 = _make_users(db)
        dm = service.start_dm(u1.id, u2.id)
        message = service.send_message(dm["id"], u1.id, "read me", ContentType.TEXT)

        # Before reading: u2 has 1 unread.
        convs_before = service.list_conversations(u2.id)
        assert next(c for c in convs_before if c["id"] == dm["id"])["unread_count"] == 1

        counts = service.mark_read(message["id"], u2.id)
        assert counts["read_count"] == 1

        convs_after = service.list_conversations(u2.id)
        assert next(c for c in convs_after if c["id"] == dm["id"])["unread_count"] == 0

    def test_mark_read_idempotent(self, db):
        service = ChatService(db)
        u1, u2 = _make_users(db)
        dm = service.start_dm(u1.id, u2.id)
        message = service.send_message(dm["id"], u1.id, "x", ContentType.TEXT)

        service.mark_read(message["id"], u2.id)
        counts = service.mark_read(message["id"], u2.id)  # second call should not double-count
        assert counts["read_count"] == 1

    def test_mark_delivered_idempotent(self, db):
        service = ChatService(db)
        u1, u2 = _make_users(db)
        dm = service.start_dm(u1.id, u2.id)
        message = service.send_message(dm["id"], u1.id, "x", ContentType.TEXT)

        service.mark_delivered(message["id"], u2.id)
        service.mark_delivered(message["id"], u2.id)  # should not raise or duplicate

        counts = service.repo.get_receipt_counts(message["id"])
        assert counts["delivered_count"] == 1


class TestCustomGroups:
    def test_create_group_makes_creator_admin_member(self, db):
        service = ChatService(db)
        u1, _ = _make_users(db)

        result = service.create_group("Study Group", "For DBMS", created_by=u1.id)
        member = service.repo.get_group_member(result["group"].id, u1.id)
        assert member is not None
        from app.models.chat import GroupMemberRole
        assert member.role_in_group == GroupMemberRole.ADMIN

    def test_add_member_by_non_admin_rejected(self, db):
        service = ChatService(db)
        u1, u2 = _make_users(db)
        outsider, _ = _make_users(db)
        result = service.create_group("Group X", None, created_by=u1.id)

        with pytest.raises(ForbiddenError):
            service.add_group_member(result["group"].id, u2.id, outsider.id)

    def test_add_member_by_admin_succeeds_and_syncs_conversation(self, db):
        service = ChatService(db)
        u1, u2 = _make_users(db)
        result = service.create_group("Group Y", None, created_by=u1.id)

        service.add_group_member(result["group"].id, u1.id, u2.id)

        member = service.repo.get_group_member(result["group"].id, u2.id)
        assert member is not None
        assert service.repo.is_participant(result["conversation_id"], u2.id) is True

    def test_delete_section_group_directly_rejected(self, db):
        """Section groups must go through the Academic domain, per the spec."""
        from app.repositories.academic_repository import AcademicRepository
        from app.repositories.chat_repository import ChatRepository

        service = ChatService(db)
        u1, _ = _make_users(db)

        academic_repo = AcademicRepository(db)
        dept = academic_repo.create_department("Test Dept", "TD1")
        program = academic_repo.create_program(dept.id, "Test Program", "TP1", 4)
        semester = academic_repo.create_semester(program.id, 1, None, None, None)
        section = academic_repo.create_section(semester.id, "Section Z")
        db.flush()

        chat_repo = ChatRepository(db)
        group, _conv = chat_repo.create_section_group_with_conversation(section.id, "Section Group", u1.id)
        db.commit()

        with pytest.raises(ValidationError) as exc_info:
            service.delete_group(group.id, u1.id)
        assert exc_info.value.code == "CANNOT_DELETE_SECTION_GROUP"

    def test_list_groups_filters_by_type(self, db):
        service = ChatService(db)
        u1, _ = _make_users(db)
        result = service.create_group("Filtered Group", None, created_by=u1.id)

        custom_groups = service.list_groups(u1.id, GroupType.CUSTOM)
        assert any(g.id == result["group"].id for g in custom_groups)

        section_groups = service.list_groups(u1.id, GroupType.SECTION)
        assert not any(g.id == result["group"].id for g in section_groups)

        all_groups = service.list_groups(u1.id)
        assert any(g.id == result["group"].id for g in all_groups)

    def test_update_group_by_admin_succeeds(self, db):
        service = ChatService(db)
        u1, _ = _make_users(db)
        result = service.create_group("Original Name", "Original Desc", created_by=u1.id)

        updated = service.update_group(result["group"].id, u1.id, "New Name", None)
        assert updated.name == "New Name"
        assert updated.description == "Original Desc"  # unchanged

    def test_update_group_by_non_admin_rejected(self, db):
        service = ChatService(db)
        u1, u2 = _make_users(db)
        result = service.create_group("Group", None, created_by=u1.id)

        with pytest.raises(ForbiddenError):
            service.update_group(result["group"].id, u2.id, "Hijacked", None)

    def test_update_unknown_group_raises_not_found(self, db):
        import uuid
        service = ChatService(db)
        u1, _ = _make_users(db)
        with pytest.raises(NotFoundError) as exc_info:
            service.update_group(uuid.uuid4(), u1.id, "X", None)
        assert exc_info.value.code == "GROUP_NOT_FOUND"

    def test_delete_unknown_group_raises_not_found(self, db):
        import uuid
        service = ChatService(db)
        u1, _ = _make_users(db)
        with pytest.raises(NotFoundError) as exc_info:
            service.delete_group(uuid.uuid4(), u1.id)
        assert exc_info.value.code == "GROUP_NOT_FOUND"

    def test_add_member_unknown_group_raises_not_found(self, db):
        import uuid
        service = ChatService(db)
        u1, u2 = _make_users(db)
        with pytest.raises(NotFoundError) as exc_info:
            service.add_group_member(uuid.uuid4(), u1.id, u2.id)
        assert exc_info.value.code == "GROUP_NOT_FOUND"

    def test_add_member_already_member_rejected(self, db):
        service = ChatService(db)
        u1, u2 = _make_users(db)
        result = service.create_group("Dup Group", None, created_by=u1.id)
        service.add_group_member(result["group"].id, u1.id, u2.id)

        with pytest.raises(ValidationError) as exc_info:
            service.add_group_member(result["group"].id, u1.id, u2.id)
        assert exc_info.value.code == "ALREADY_MEMBER"

    def test_remove_member_by_admin_succeeds(self, db):
        service = ChatService(db)
        u1, u2 = _make_users(db)
        result = service.create_group("Removable Group", None, created_by=u1.id)
        service.add_group_member(result["group"].id, u1.id, u2.id)

        service.remove_group_member(result["group"].id, u1.id, u2.id)

        member = service.repo.get_group_member(result["group"].id, u2.id)
        assert member is None
        assert service.repo.is_participant(result["conversation_id"], u2.id) is False

    def test_remove_member_unknown_group_raises(self, db):
        import uuid
        service = ChatService(db)
        u1, u2 = _make_users(db)
        with pytest.raises(NotFoundError) as exc_info:
            service.remove_group_member(uuid.uuid4(), u1.id, u2.id)
        assert exc_info.value.code == "GROUP_NOT_FOUND"


class TestMessageEditEdgeCases:
    def test_edit_deleted_message_rejected(self, db):
        service = ChatService(db)
        u1, u2 = _make_users(db)
        dm = service.start_dm(u1.id, u2.id)
        message = service.send_message(dm["id"], u1.id, "gone soon", ContentType.TEXT)
        service.delete_message(message["id"], u1.id)

        with pytest.raises(ValidationError) as exc_info:
            service.edit_message(message["id"], u1.id, "resurrected")
        assert exc_info.value.code == "MESSAGE_DELETED"

    def test_edit_nonexistent_message_raises(self, db):
        import uuid
        service = ChatService(db)
        u1, _ = _make_users(db)
        with pytest.raises(NotFoundError) as exc_info:
            service.edit_message(uuid.uuid4(), u1.id, "x")
        assert exc_info.value.code == "MESSAGE_NOT_FOUND"

    def test_delete_message_by_non_owner_rejected(self, db):
        service = ChatService(db)
        u1, u2 = _make_users(db)
        dm = service.start_dm(u1.id, u2.id)
        message = service.send_message(dm["id"], u1.id, "mine", ContentType.TEXT)

        with pytest.raises(ForbiddenError):
            service.delete_message(message["id"], u2.id)

    def test_history_pagination_with_before_cursor(self, db):
        service = ChatService(db)
        u1, u2 = _make_users(db)
        dm = service.start_dm(u1.id, u2.id)
        for i in range(3):
            service.send_message(dm["id"], u1.id, f"msg {i}", ContentType.TEXT)

        first_page = service.get_message_history(dm["id"], u1.id, before=None, limit=2)
        assert len(first_page["items"]) == 2
        assert first_page["has_more"] is True

        second_page = service.get_message_history(
            dm["id"], u1.id, before=first_page["next_cursor"], limit=2
        )
        assert len(second_page["items"]) == 1
        assert second_page["has_more"] is False

    def test_read_receipt_on_unknown_message_raises(self, db):
        import uuid
        service = ChatService(db)
        u1, _ = _make_users(db)
        with pytest.raises(NotFoundError) as exc_info:
            service.mark_read(uuid.uuid4(), u1.id)
        assert exc_info.value.code == "MESSAGE_NOT_FOUND"
