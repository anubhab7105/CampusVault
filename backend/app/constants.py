"""App-wide UPPER_SNAKE_CASE constants.

Values here are product/domain constants (not secrets). Environment-specific
values live in app/config.py.
"""

from __future__ import annotations

from typing import Final

# --- Roles ---------------------------------------------------------------- #
ROLE_STUDENT: Final[str] = "Student"
ROLE_TEACHER: Final[str] = "Teacher"
ROLE_ADMIN: Final[str] = "Admin"
SYSTEM_ROLES: Final[frozenset[str]] = frozenset(
    {ROLE_STUDENT, ROLE_TEACHER, ROLE_ADMIN}
)

# --- Auth providers -------------------------------------------------------- #
AUTH_PROVIDER_GOOGLE: Final[str] = "google"
AUTH_PROVIDER_OTP: Final[str] = "otp"

# --- Chat ------------------------------------------------------------------ #
CONVERSATION_GROUP: Final[str] = "group"
CONVERSATION_DIRECT: Final[str] = "direct"
CONVERSATION_TYPES: Final[frozenset[str]] = frozenset(
    {CONVERSATION_GROUP, CONVERSATION_DIRECT}
)

MESSAGE_TYPE_TEXT: Final[str] = "text"
MESSAGE_TYPE_FILE: Final[str] = "file"
MESSAGE_TYPE_SYSTEM: Final[str] = "system"
MESSAGE_TYPES: Final[frozenset[str]] = frozenset(
    {MESSAGE_TYPE_TEXT, MESSAGE_TYPE_FILE, MESSAGE_TYPE_SYSTEM}
)

# --- Library ---------------------------------------------------------------- #
RESOURCE_TYPES: Final[frozenset[str]] = frozenset(
    {"note", "book", "past_paper", "slide", "link"}
)
VISIBILITY_CHOICES: Final[frozenset[str]] = frozenset(
    {"section", "subject", "department", "college", "private"}
)

# --- Uploads / scanning ------------------------------------------------------- #
SCAN_STATUS_PENDING: Final[str] = "pending"
SCAN_STATUS_CLEAN: Final[str] = "clean"
SCAN_STATUS_INFECTED: Final[str] = "infected"
SCAN_STATUS_FAILED: Final[str] = "failed"
SCAN_STATUSES: Final[frozenset[str]] = frozenset(
    {
        SCAN_STATUS_PENDING, SCAN_STATUS_CLEAN,
        SCAN_STATUS_INFECTED, SCAN_STATUS_FAILED,
    }
)

# --- Notifications ------------------------------------------------------------ #
NOTIFICATION_SYSTEM: Final[str] = "system"
NOTIFICATION_TYPES: Final[frozenset[str]] = frozenset(
    {"resource_shared", "group_message", "moderation", NOTIFICATION_SYSTEM}
)

# --- Academic hierarchy depth guard ---------------------------------------------- #
MAX_SEMESTER_COUNT: Final[int] = 12

# --- Pagination ---------------------------------------------------------------- #
DEFAULT_PAGE_SIZE: Final[int] = 20
MAX_PAGE_SIZE: Final[int] = 100

# --- Error codes (mirror docs/08_API_GUIDE.md) -------------------------------------- #
VALIDATION_ERROR: Final[str] = "VALIDATION_ERROR"
UNAUTHORIZED: Final[str] = "UNAUTHORIZED"
FORBIDDEN: Final[str] = "FORBIDDEN"
NOT_FOUND: Final[str] = "NOT_FOUND"
CONFLICT: Final[str] = "CONFLICT"
RATE_LIMITED: Final[str] = "RATE_LIMITED"
INTERNAL_ERROR: Final[str] = "INTERNAL_ERROR"
SERVICE_UNAVAILABLE: Final[str] = "SERVICE_UNAVAILABLE"
