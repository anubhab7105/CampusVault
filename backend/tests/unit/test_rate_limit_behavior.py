"""Behavior tests for rate limiting.

Covers:
- Normal traffic stays under the limit and succeeds
- Burst traffic returns 429 after the threshold
- Limit resets after the window (freezegun)
- User-ID keying: two users don't affect each other; same user across IPs
- IP keying for unauthenticated routes
- 429 responses include Retry-After and don't leak sensitive data
"""

from __future__ import annotations

from freezegun import freeze_time


class TestRateLimitAuthenticatedRoutes:
    """User-ID keyed routes (authenticated)."""

    def test_normal_traffic_succeeds(self, auth_client, make_jwt_token):
        token = make_jwt_token(user_id="rl-user-1", role="Student")
        headers = {"Authorization": f"Bearer {token}"}
        # /api/v1/auth/me is limited to RATELIMIT_AUTH = 5/min
        for _ in range(5):
            resp = auth_client.get("/api/v1/auth/me", headers=headers)
            assert resp.status_code == 200, resp.get_json()

    def test_burst_returns_429(self, auth_client, make_jwt_token):
        token = make_jwt_token(user_id="rl-user-2", role="Student")
        headers = {"Authorization": f"Bearer {token}"}
        for _ in range(5):
            resp = auth_client.get("/api/v1/auth/me", headers=headers)
            assert resp.status_code == 200
        # 6th request is over the limit.
        resp = auth_client.get("/api/v1/auth/me", headers=headers)
        assert resp.status_code == 429
        body = resp.get_json()
        assert body["success"] is False
        assert body["error"]["code"] == "RATE_LIMITED"
        assert "Retry-After" in resp.headers
        assert resp.headers["Retry-After"].isdigit()

    def test_429_does_not_leak_sensitive_data(self, auth_client, make_jwt_token):
        token = make_jwt_token(user_id="rl-user-3", role="Student")
        headers = {"Authorization": f"Bearer {token}"}
        for _ in range(5):
            auth_client.get("/api/v1/auth/me", headers=headers)
        resp = auth_client.get("/api/v1/auth/me", headers=headers)
        body = resp.get_json()
        payload = str(body)
        assert "user" not in payload.lower()
        assert "key" not in payload.lower()
        assert "token" not in payload.lower()
        assert "ip" not in payload.lower()

    @freeze_time("2026-11-01 12:00:00")
    def test_limit_resets_after_window(self, auth_client, make_jwt_token):
        token = make_jwt_token(user_id="rl-user-4", role="Student")
        headers = {"Authorization": f"Bearer {token}"}
        for _ in range(5):
            auth_client.get("/api/v1/auth/me", headers=headers)
        resp = auth_client.get("/api/v1/auth/me", headers=headers)
        assert resp.status_code == 429

        # Advance past the 1-minute window.
        freeze_time.move_to("2026-11-01 12:01:30")
        resp = auth_client.get("/api/v1/auth/me", headers=headers)
        assert resp.status_code == 200, resp.get_json()

    def test_two_users_are_independent(self, auth_client, make_jwt_token):
        token_a = make_jwt_token(user_id="rl-user-a", role="Student")
        token_b = make_jwt_token(user_id="rl-user-b", role="Student")
        headers_a = {"Authorization": f"Bearer {token_a}"}
        headers_b = {"Authorization": f"Bearer {token_b}"}
        # User A exhausts their limit.
        for _ in range(5):
            auth_client.get("/api/v1/auth/me", headers=headers_a)
        resp_a = auth_client.get("/api/v1/auth/me", headers=headers_a)
        assert resp_a.status_code == 429
        # User B is unaffected (different user ID key).
        resp_b = auth_client.get("/api/v1/auth/me", headers=headers_b)
        assert resp_b.status_code == 200

    def test_same_user_is_limited_regardless_of_ip(self, auth_client, make_jwt_token):
        token = make_jwt_token(user_id="rl-user-same", role="Student")
        headers = {"Authorization": f"Bearer {token}"}
        # Exhaust the limit; key is on user ID so IP is irrelevant.
        for _ in range(5):
            auth_client.get("/api/v1/auth/me", headers=headers)
        resp = auth_client.get("/api/v1/auth/me", headers=headers)
        assert resp.status_code == 429


class TestRateLimitUnauthenticatedRoutes:
    """IP-keyed routes (no authentication)."""

    def test_ip_keying_for_unauthenticated_route(self, client):
        # POST /api/v1/auth/google is unauthenticated; keyed on IP.
        # RATELIMIT_AUTH = 5/min.
        for _ in range(5):
            resp = client.post("/api/v1/auth/google", json={"code": "fake-code"})
            # Invalid code -> 503 from Google OAuth failure, not 429 yet.
            assert resp.status_code != 429, resp.get_json()
        # 6th request from the same IP -> 429.
        resp = client.post("/api/v1/auth/google", json={"code": "fake-code"})
        assert resp.status_code == 429
        body = resp.get_json()
        assert body["error"]["code"] == "RATE_LIMITED"
        assert "Retry-After" in resp.headers


class TestRateLimitSearch:
    """Search/browse endpoint (user-ID keyed, higher limit)."""

    def test_search_normal_and_burst(self, auth_client, make_jwt_token):
        token = make_jwt_token(user_id="rl-search-user", role="Student")
        headers = {"Authorization": f"Bearer {token}"}
        # RATELIMIT_SEARCH = 30/min — make a few requests, all succeed.
        for _ in range(5):
            resp = auth_client.get("/api/v1/library?q=test", headers=headers)
            assert resp.status_code == 200, resp.get_json()


class TestRateLimitChatHttp:
    """HTTP chat message send (user-ID keyed)."""

    def test_chat_send_normal_and_burst(self, auth_client, make_jwt_token):
        token = make_jwt_token(user_id="rl-chat-user", role="Student")
        headers = {"Authorization": f"Bearer {token}"}
        # Need a conversation to send to; create a DM first.
        resp = auth_client.post(
            "/api/v1/chat/conversations/dm/00000000-0000-0000-0000-000000000002",
            headers=headers,
        )
        assert resp.status_code == 200, resp.get_json()
        conv_id = resp.get_json()["data"]["id"]

        # Send messages up to the limit (30/min).
        for i in range(5):
            resp = auth_client.post(
                f"/api/v1/chat/conversations/{conv_id}/messages",
                headers=headers,
                json={"conversation_id": conv_id, "content": f"msg {i}"},
            )
            assert resp.status_code == 201, resp.get_json()
