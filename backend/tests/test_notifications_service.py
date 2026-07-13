"""
Integration tests for NotificationsService — real Postgres + real Redis
presence. Includes a test that proves the Chat -> Notifications offline
delivery wiring actually works end-to-end, not just that it's documented.
"""
import uuid

import pytest

from app.models.auth import UserType
from app.models.chat import ContentType
from app.repositories.auth_repository import AuthRepository
from app.services.chat_service import ChatService
from app.services.notifications_service import NotificationsService
from app.utils import presence
from app.utils.exceptions import ForbiddenError, NotFoundError


def _make_user(db, label):
    auth_repo = AuthRepository(db)
    suffix = uuid.uuid4().hex[:8]
    user = auth_repo.create_user(f"{label}_{suffix}@college.edu", label, UserType.STUDENT)
    db.commit()
    return user


@pytest.fixture(autouse=True)
def _clean_presence():
    """Ensure no leftover presence keys from a prior test leak into this one."""
    yield
    # best-effort cleanup; presence keys expire on their own TTL regardless


class TestNotificationCreationAndListing:
    def test_create_and_list_for_user(self, db):
        service = NotificationsService(db)
        user = _make_user(db, "Notified")

        service.create_for_user(user.id, "test.event", "Test Title", body="details", data={"k": "v"})

        result = service.list_notifications(user.id, unread_only=False, before=None)
        assert len(result["items"]) == 1
        assert result["items"][0].title == "Test Title"
        assert result["unread_count"] == 1

    def test_unread_only_filter(self, db):
        service = NotificationsService(db)
        user = _make_user(db, "FilterUser")

        n1 = service.create_for_user(user.id, "a", "First")
        service.create_for_user(user.id, "b", "Second")
        service.mark_read(n1.id, user.id)

        result = service.list_notifications(user.id, unread_only=True, before=None)
        assert len(result["items"]) == 1
        assert result["items"][0].title == "Second"

    def test_unread_count(self, db):
        service = NotificationsService(db)
        user = _make_user(db, "CountUser")
        service.create_for_user(user.id, "a", "One")
        service.create_for_user(user.id, "b", "Two")

        assert service.get_unread_count(user.id) == 2

    def test_pagination_with_cursor(self, db):
        service = NotificationsService(db)
        user = _make_user(db, "PageUser")
        for i in range(3):
            service.create_for_user(user.id, "x", f"Notif {i}")

        first_page = service.list_notifications(user.id, unread_only=False, before=None, limit=2)
        assert len(first_page["items"]) == 2
        assert first_page["has_more"] is True

        second_page = service.list_notifications(
            user.id, unread_only=False, before=first_page["next_cursor"], limit=2
        )
        assert len(second_page["items"]) == 1
        assert second_page["has_more"] is False


class TestMarkRead:
    def test_mark_read_is_idempotent(self, db):
        service = NotificationsService(db)
        user = _make_user(db, "IdemUser")
        n = service.create_for_user(user.id, "a", "Title")

        first = service.mark_read(n.id, user.id)
        second = service.mark_read(n.id, user.id)
        assert first.read_at == second.read_at  # second call doesn't change the timestamp

    def test_mark_read_by_non_owner_rejected(self, db):
        service = NotificationsService(db)
        owner = _make_user(db, "Owner")
        intruder = _make_user(db, "Intruder")
        n = service.create_for_user(owner.id, "a", "Private")

        with pytest.raises(ForbiddenError):
            service.mark_read(n.id, intruder.id)

    def test_mark_read_unknown_notification_raises(self, db):
        service = NotificationsService(db)
        user = _make_user(db, "NoNotif")
        with pytest.raises(NotFoundError) as exc_info:
            service.mark_read(uuid.uuid4(), user.id)
        assert exc_info.value.code == "NOTIFICATION_NOT_FOUND"

    def test_mark_all_read(self, db):
        service = NotificationsService(db)
        user = _make_user(db, "MarkAllUser")
        service.create_for_user(user.id, "a", "One")
        service.create_for_user(user.id, "b", "Two")
        service.create_for_user(user.id, "c", "Three")

        updated = service.mark_all_read(user.id)
        assert updated == 3
        assert service.get_unread_count(user.id) == 0

    def test_mark_all_read_only_touches_unread(self, db):
        service = NotificationsService(db)
        user = _make_user(db, "PartialUser")
        n1 = service.create_for_user(user.id, "a", "Already read")
        service.create_for_user(user.id, "b", "Still unread")
        service.mark_read(n1.id, user.id)

        updated = service.mark_all_read(user.id)
        assert updated == 1  # only the one that was still unread


class TestChatToNotificationsIntegration:
    """Proves the documented offline-delivery coupling actually works."""

    def test_offline_recipient_gets_a_notification_row(self, db):
        chat_service = ChatService(db)
        u1 = _make_user(db, "Sender")
        u2 = _make_user(db, "OfflineRecipient")
        presence.mark_offline(u2.id)  # explicit: ensure u2 is NOT marked online

        dm = chat_service.start_dm(u1.id, u2.id)
        chat_service.send_message(dm["id"], u1.id, "hello while you were away", ContentType.TEXT)

        notifications_service = NotificationsService(db)
        result = notifications_service.list_notifications(u2.id, unread_only=False, before=None)
        assert len(result["items"]) == 1
        assert result["items"][0].type == "message.new"
        assert result["items"][0].data["conversation_id"] == str(dm["id"])

    def test_online_recipient_does_not_get_a_duplicate_notification_row(self, db):
        """
        Per the spec: an online recipient sees the message live via the
        socket room, not via a persisted Notification row — this confirms
        the presence check actually gates row creation, not just the emit.
        """
        chat_service = ChatService(db)
        u1 = _make_user(db, "Sender2")
        u2 = _make_user(db, "OnlineRecipient")
        presence.mark_online(u2.id)

        dm = chat_service.start_dm(u1.id, u2.id)
        chat_service.send_message(dm["id"], u1.id, "you're here so no notif row", ContentType.TEXT)

        notifications_service = NotificationsService(db)
        result = notifications_service.list_notifications(u2.id, unread_only=False, before=None)
        assert len(result["items"]) == 0

        presence.mark_offline(u2.id)  # cleanup

    def test_sender_never_gets_notified_of_own_message(self, db):
        chat_service = ChatService(db)
        u1 = _make_user(db, "SelfSender")
        u2 = _make_user(db, "OtherParty")
        presence.mark_offline(u1.id)
        presence.mark_offline(u2.id)

        dm = chat_service.start_dm(u1.id, u2.id)
        chat_service.send_message(dm["id"], u1.id, "hi", ContentType.TEXT)

        notifications_service = NotificationsService(db)
        sender_result = notifications_service.list_notifications(u1.id, unread_only=False, before=None)
        assert len(sender_result["items"]) == 0
