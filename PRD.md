# CampusVault --- Product Requirements Document (PRD)

**Document status:** Draft --- consolidated product specification\
**Version:** 1.0\
**Last updated:** 28 October 2026\
**Repository:** https://github.com/anubhab7105/CampusVault\
**Product type:** Web-based academic resource library and collaboration
platform

> **Scope note:** This PRD consolidates the product direction and
> technical plans documented in the repository. Features described as
> planned or target behavior should not be interpreted as proof that
> every feature is currently implemented. The repository's stabilization
> notes report that the baseline still requires additional
> lint/type/build verification.

------------------------------------------------------------------------

## 1. Executive Summary

CampusVault is an online academic library and collaboration platform for
a college community. It provides students and teachers with a central
place to discover, publish, organize, and access academic resources,
collaborate through conversations and groups, and receive safer
file-sharing support through malware scanning. Administrators manage
users, academic structures, resources, moderation, audit records, and
system-level visibility.

The product is designed as a role-aware web application with a React
single-page frontend and a Flask API backend. PostgreSQL stores
application data, Supabase Storage stores uploaded files, Redis supports
caching and real-time coordination, and Celery handles background work
such as file scanning and scheduled analytics.

CampusVault should prioritize reliable access to learning materials,
clear permissions, accessible user journeys, privacy-conscious
analytics, and maintainable operations.

## 2. Problem Statement

Academic resources are often distributed across messaging groups,
personal drives, email threads, and informal sharing channels. This
makes it difficult to find current, relevant material, understand
whether a resource is trustworthy, manage access consistently, and
maintain a useful academic knowledge base.

CampusVault addresses these problems by offering: - A unified,
searchable academic resource library. - Academic organization by
department, program, semester, section, and subject. - Role- and
membership-aware resource visibility. - Resource upload, publication,
download, and moderation workflows. - Group conversations and real-time
collaboration. - Malware-scanning status and quarantine workflows. -
Administrative management, auditability, and aggregate operational
analytics.

## 3. Product Vision

Make CampusVault a dependable, secure, and easy-to-use digital academic
hub where college communities can organize learning resources and
collaborate without losing control over access, safety, or governance.

### 3.1 Product Principles

1.  **Security by default:** deny access unless permissions explicitly
    allow it.
2.  **Academic relevance:** organize and filter content around the
    institution's academic hierarchy.
3.  **Privacy by design:** analytics are aggregate-only and do not
    expose individual reading habits or message/file content.
4.  **Transparency:** users and administrators can understand resource
    scan status and meaningful failure states.
5.  **Accessibility:** primary flows should work with keyboard
    navigation, clear focus states, labels, and assistive technologies.
6.  **Operational reliability:** background tasks, external
    dependencies, and failures must be observable and recoverable.
7.  **Maintainability:** API contracts, migrations, tests, and
    engineering documentation must evolve with the implementation.

## 4. Goals and Success Metrics

### 4.1 Product Goals

-   Provide a single source of truth for academic learning resources.
-   Reduce the effort required to find relevant material.
-   Enable teachers to share and manage resources with appropriate
    audiences.
-   Enable students to collaborate through groups and conversations.
-   Reduce the risk of distributing malicious files.
-   Give administrators sufficient tools to govern the platform
    responsibly.
-   Establish production-oriented engineering practices and release
    checks.

### 4.2 Proposed Success Metrics

Targets below are product goals and should be validated against real
usage after instrumentation is available.

  -----------------------------------------------------------------------
  Area                    Metric                  Initial target
  ----------------------- ----------------------- -----------------------
  Discovery               Median time to find a   Under 60 seconds in
                          known resource          usability tests

  Search                  Search requests         At least 80% in a
                          returning relevant      curated test set
                          results                 

  Reliability             Successful API requests At least 99.5% monthly
                          excluding expected      
                          client errors           

  Performance             API p95 latency for     Under 300 ms on a
                          common read endpoints   representative seeded
                                                  dataset

  Web performance         Lighthouse score on     Above 90 where feasible
                          Login, Library, Chat,   
                          and Admin               

  Security                Unauthorized-access     100% pass
                          regression tests        

  File safety             Uploaded files receive  At least 99% within the
                          a terminal scan state   defined processing SLA

  Quality                 Test coverage           80% target for
                                                  release-ready code

  Operations              Recovery from a         Runbook-tested; target
                          documented service      RTO 4 hours
                          incident                

  Privacy                 Analytics payloads      Zero
                          containing message/file 
                          content or unnecessary  
                          PII                     
  -----------------------------------------------------------------------

Metrics should be measured with documented datasets, test conditions,
and privacy safeguards. Targets must not be represented as achieved
until evidence is recorded.

## 5. Users and Roles

### 5.1 Student

Needs to find course-relevant notes, assignments, reference material,
and shared resources; download permitted files; participate in groups;
and receive clear feedback when an item is unavailable or unsafe.

### 5.2 Teacher

Needs to publish and organize academic resources, share them with
relevant students or groups, collaborate with colleagues/students, and
understand whether uploaded files are available for use.

### 5.3 Administrator

Needs to manage users and roles, maintain academic structure, moderate
resources, oversee suspicious or failed scans, review audit events, and
understand platform-level activity and service health.

### 5.4 System/Background Worker

Performs non-interactive work such as file scanning, notifications,
analytics aggregation, retries, and scheduled cleanup. Background tasks
must be idempotent where practical and must not bypass authorization or
audit requirements.

## 6. Scope

### 6.1 In Scope

-   Authentication and role-based access control.
-   User profile and account status management.
-   Academic hierarchy management.
-   Academic resource upload, metadata, publication, browsing, search,
    download, and moderation.
-   File scanning, scan status, quarantine, and recovery workflows.
-   Group/conversation features and real-time message delivery.
-   Notifications and notification preferences where configured.
-   Admin dashboard and aggregate analytics.
-   Append-only audit logging and admin-only CSV export.
-   Operational health checks, structured logs, dependency checks, and
    deployment documentation.
-   Automated unit, integration, frontend, and end-to-end testing.

### 6.2 Out of Scope for the Initial Release

-   Native Android/iOS applications.
-   Public social networking unrelated to academic collaboration.
-   Selling or advertising against user data.
-   Per-student surveillance dashboards or individual reading-habit
    analytics.
-   AI-generated academic answers or grading unless separately approved.
-   A guarantee that malware scanning detects every malicious file.
-   Institution-wide integrations (SIS/LMS/SSO) unless separately
    specified and scoped.
-   Payments, subscriptions, or a public marketplace.

## 7. Core User Journeys

### 7.1 Sign In and Access the Platform

1.  User opens CampusVault.
2.  User signs in through the supported authentication flow.
3.  The server validates credentials/session and determines the user's
    authorized role and scope.
4.  The frontend displays only routes and actions appropriate to the
    user's permissions.
5.  Expired or invalid sessions receive a clear recovery path.

**Acceptance criteria** - Invalid credentials do not disclose whether a
particular account exists. - Protected API endpoints reject
unauthenticated requests. - Authorization is enforced server-side, not
only by hiding frontend controls. - Refresh credentials are stored using
appropriately protected cookies; tokens and secrets are not logged.

### 7.2 Find an Academic Resource

1.  User opens the library or global search.
2.  User enters keywords and optionally applies filters such as resource
    type, department, program, semester, section, subject, visibility,
    and publication status.
3.  Results are ranked and display useful metadata and safe text
    snippets.
4.  The server filters results to resources the current user is allowed
    to see.
5.  User opens a resource detail view and downloads it if authorized and
    available.

**Acceptance criteria** - Search supports title and descriptive
metadata. - Search results never reveal inaccessible resources or group
names. - Empty, loading, and error states are clear. - Search input
supports keyboard interaction and accessible labeling. - Snippets are
safely escaped; search input is validated.

### 7.3 Upload and Publish a Resource

1.  Authorized user selects a file and enters metadata.
2.  Server validates file type, size, metadata, and permissions.
3.  File is stored in the configured storage service and queued for
    scanning.
4.  The resource records a scan state such as pending, scanning, clean,
    infected, or failed.
5.  Only resources permitted by policy are made available for
    download/publication.
6.  User receives a clear success, pending, or failure state.

**Acceptance criteria** - File size and allowed-type limits are
configurable by environment. - Storage keys are not guessable
identifiers that grant access by themselves. - Uploads and downloads are
authorized server-side. - Failed scanning is not silently represented as
clean. - Duplicate/retried background jobs do not corrupt resource
state. - The application communicates that scanning reduces risk but is
not a perfect guarantee.

### 7.4 Collaborate in a Group

1.  User opens a group or conversation they are authorized to access.
2.  The frontend loads message history with pagination.
3.  User sends a message; the server validates membership and message
    constraints.
4.  The message is persisted and delivered to eligible participants
    through the real-time layer.
5.  Edit, deletion, ownership-transfer, and archive behavior follow the
    applicable permissions and policy.

**Acceptance criteria** - Non-members cannot read or send messages to a
restricted conversation. - Real-time events are scoped to authorized
participants. - Message history uses stable ordering and pagination. -
Connection loss and retry states are handled without duplicate visible
messages. - Message edit windows and moderation rules are enforced
server-side.

### 7.5 Administrator Manages the Platform

1.  Administrator opens the admin dashboard.
2.  Dashboard displays aggregate user, resource, storage,
    upload/download, scan, and collaboration statistics.
3.  Administrator can search and filter users, manage roles/status,
    maintain academic structure, moderate resources, and inspect audit
    logs.
4.  Sensitive actions require confirmation and produce an audit event.
5.  Administrator can export filtered audit records where authorized.

**Acceptance criteria** - Admin APIs require server-validated
administrative privileges. - Users cannot deactivate themselves through
the admin workflow. - Academic hierarchy constraints prevent invalid
parent-child relationships. - Moderation actions record actor, target,
timestamp, action, and reason where applicable. - Audit logs are
append-only from the application's perspective; updates/deletes are
prohibited. - CSV exports are streamed where appropriate and protect
against spreadsheet formula injection.

## 8. Functional Requirements

Priority definitions: **P0** = required for a safe core release; **P1**
= important for a complete release; **P2** = later enhancement.

### 8.1 Identity and Access

-   **FR-AUTH-01 (P0):** Authenticate users using the repository's
    supported authentication flow.
-   **FR-AUTH-02 (P0):** Enforce server-side role-based access for
    Student, Teacher, and Admin capabilities.
-   **FR-AUTH-03 (P0):** Validate session/token expiry and provide a
    safe refresh/logout lifecycle.
-   **FR-AUTH-04 (P0):** Store refresh tokens in appropriately
    configured HttpOnly, Secure, SameSite cookies in production.
-   **FR-AUTH-05 (P0):** Apply rate limits to authentication and other
    abuse-sensitive endpoints.
-   **FR-AUTH-06 (P1):** Support configured email OTP/verification and
    resend/expiry policies.
-   **FR-AUTH-07 (P0):** Record security-sensitive account and
    permission changes in the audit log.

### 8.2 Academic Structure

-   **FR-ACADEMIC-01 (P0):** Represent department, program, semester,
    section, and subject relationships.
-   **FR-ACADEMIC-02 (P0):** Validate hierarchy relationships on
    create/update.
-   **FR-ACADEMIC-03 (P1):** Allow administrators to create, update,
    deactivate, and manage academic entities.
-   **FR-ACADEMIC-04 (P0):** Prevent destructive operations that would
    orphan dependent records; use soft deletion where defined.

### 8.3 Resource Library

-   **FR-LIB-01 (P0):** Store resource metadata including title,
    description, type, uploader, academic associations, visibility,
    publication state, and timestamps.
-   **FR-LIB-02 (P0):** Support authorized file upload and download
    through configured storage.
-   **FR-LIB-03 (P0):** Support browse/list views with pagination and
    relevant filters.
-   **FR-LIB-04 (P0):** Enforce visibility and membership rules in the
    backend repository/service layer.
-   **FR-LIB-05 (P1):** Support global search across permitted resources
    and groups.
-   **FR-LIB-06 (P1):** Rank search results, provide safe snippets, and
    tolerate reasonable spelling variation where supported by the
    database.
-   **FR-LIB-07 (P0):** Track resource lifecycle and availability
    states, including unpublished, inactive, quarantined, or deleted
    states as appropriate.
-   **FR-LIB-08 (P1):** Maintain download/upload counters for aggregate
    reporting without exposing individual behavioral profiles.

### 8.4 File Safety and Moderation

-   **FR-FILE-01 (P0):** Validate file extension/type, size, and request
    content before processing.
-   **FR-FILE-02 (P0):** Queue file scans through the background task
    system.
-   **FR-FILE-03 (P0):** Track scan status as pending, scanning, clean,
    infected, or failed.
-   **FR-FILE-04 (P0):** Do not treat scanner errors/timeouts as
    successful clean scans.
-   **FR-FILE-05 (P1):** Provide an administrator queue for infected and
    failed files.
-   **FR-FILE-06 (P1):** Support justified quarantine, deletion,
    restoration for review, and re-scan actions.
-   **FR-FILE-07 (P0):** Audit moderation actions and prevent
    unauthorized access to quarantined objects.
-   **FR-FILE-08 (P1):** Notify the uploader when scan processing fails
    or requires action.

### 8.5 Groups and Messaging

-   **FR-CHAT-01 (P0):** Support authorized conversations/groups and
    participant membership.
-   **FR-CHAT-02 (P0):** Persist messages and return paginated history.
-   **FR-CHAT-03 (P1):** Deliver eligible real-time events through
    Socket.IO.
-   **FR-CHAT-04 (P0):** Validate membership and permission for every
    read/write action.
-   **FR-CHAT-05 (P1):** Support group archive and ownership transfer
    under defined constraints.
-   **FR-CHAT-06 (P1):** Enforce configured message edit windows and
    message validation.
-   **FR-CHAT-07 (P0):** Exclude message bodies from analytics
    aggregates.

### 8.6 Notifications

-   **FR-NOTIFY-01 (P1):** Send configured transactional notifications
    for relevant events.
-   **FR-NOTIFY-02 (P1):** Respect user notification preferences where
    implemented.
-   **FR-NOTIFY-03 (P0):** Retry transient delivery failures with
    bounded retries and observable failure states.
-   **FR-NOTIFY-04 (P0):** Never expose credentials, private file URLs,
    or sensitive content in notification logs.

### 8.7 Administration and Analytics

-   **FR-ADMIN-01 (P1):** Show aggregate counts for users by role,
    active users, resources, storage, uploads/downloads, scan outcomes,
    and chat activity.
-   **FR-ADMIN-02 (P0):** Search/filter users and activate/deactivate
    accounts with audit logging.
-   **FR-ADMIN-03 (P0):** Manage roles only through authorized admin
    actions.
-   **FR-ADMIN-04 (P1):** Manage academic entities and validate
    relationships.
-   **FR-ADMIN-05 (P1):** Moderate resources and view scan status.
-   **FR-ADMIN-06 (P1):** Manage teacher allowlist entries where the
    allowlist flow is enabled.
-   **FR-ADMIN-07 (P1):** Filter audit events by actor, action, target,
    date range, and request identifier.
-   **FR-ADMIN-08 (P1):** Export audit events to CSV with authorization,
    safe encoding, and an audit record of the export.
-   **FR-ADMIN-09 (P0):** Restrict analytics endpoints to aggregate
    metrics; do not expose per-user activity rows or content.
-   **FR-ADMIN-10 (P1):** Display pending/stuck scans and failed
    notification deliveries that need attention.

### 8.8 Search

-   **FR-SEARCH-01 (P1):** Provide a unified search endpoint for
    resources and permitted groups.
-   **FR-SEARCH-02 (P1):** Support filters for academic scope, resource
    type, visibility, and publication state.
-   **FR-SEARCH-03 (P0):** Apply permission filters before returning
    results.
-   **FR-SEARCH-04 (P1):** Debounce frontend search requests and provide
    loading, empty, and failure states.
-   **FR-SEARCH-05 (P1):** Support keyboard focus shortcut (Ctrl/Cmd+K),
    Escape-to-close, and accessible autocomplete behavior.
-   **FR-SEARCH-06 (P2):** Store a limited number of recent searches
    locally with a clear-history control; do not sync them to the server
    by default.

### 8.9 System Health and Operations

-   **FR-OPS-01 (P0):** Expose a basic health endpoint and
    dependency-specific checks for database, Redis, storage, scanner,
    and Celery where configured.
-   **FR-OPS-02 (P1):** Emit structured logs with request/correlation
    identifiers.
-   **FR-OPS-03 (P1):** Expose internal-only metrics for request
    volume/latency, socket connections, queue depth, scan duration, and
    error rates.
-   **FR-OPS-04 (P0):** Apply bounded timeouts to external service
    calls.
-   **FR-OPS-05 (P0):** Retry transient background-task failures with
    backoff and a terminal failure/dead-letter path.
-   **FR-OPS-06 (P1):** Document backup, restore, incident response,
    deployment, and rollback procedures.
-   **FR-OPS-07 (P0):** Fail fast at startup when required production
    secrets/configuration are missing or unsafe.

## 9. Non-Functional Requirements

### 9.1 Security

-   Use TLS in staging/production.
-   Keep secrets out of source control, frontend bundles, logs, and
    error messages.
-   Validate all untrusted input on the server.
-   Use parameterized ORM/database operations.
-   Apply least privilege to database, storage, worker, and service
    credentials.
-   Configure CORS with environment-specific allowlists.
-   Apply appropriate security headers, including HSTS in production,
    content-type protection, frame protection, and a reviewed Content
    Security Policy.
-   Prevent IDOR/BOLA by checking authorization against the target
    object on every request.
-   Rate-limit sensitive routes and test route coverage automatically.
-   Scan dependencies and secrets in CI.
-   Use secure cookie flags and CSRF protections appropriate to the
    chosen authentication pattern.
-   Avoid placing private file access credentials in permanent public
    URLs.
-   Record privileged actions in tamper-resistant/append-only audit
    records.

### 9.2 Privacy and Data Governance

-   Collect only data required to operate the platform.
-   Analytics must be aggregate-only and must not include message
    content, file contents, or unnecessary PII.
-   Do not build per-user reading-habit analytics.
-   Restrict audit-log access to authorized personnel and define
    retention according to applicable institutional/legal requirements.
-   Define retention and deletion behavior for accounts, resources,
    conversations, files, and backups before production use.
-   Document data flows and the purpose of each third-party service.

### 9.3 Performance

-   Common API reads should target p95 under 300 ms on a representative
    dataset, excluding long-running file processing.
-   Use pagination for list/history endpoints.
-   Index frequently filtered and joined columns.
-   Use PostgreSQL full-text search and suitable indexes where
    supported.
-   Cache suitable aggregate/read-heavy results with explicit TTL and
    invalidation rules.
-   Keep heavy work such as file scanning and scheduled aggregation off
    request threads.
-   Use route-level frontend code splitting and optimize images/assets.

### 9.4 Reliability and Resilience

-   Background tasks should be retryable and idempotent.
-   Dependency outages must produce explicit degraded/failure states
    rather than false success.
-   Use health checks and bounded timeouts.
-   Provide graceful shutdown and safe worker restart behavior.
-   Document recovery objectives; the engineering plan proposes RPO of 1
    hour and RTO of 4 hours, which must be validated by restore drills.
-   A failed scanner should be visible to users/admins and must not
    silently mark a file clean.

### 9.5 Accessibility and Usability

-   Support keyboard-only navigation for core flows.
-   Provide labels, meaningful headings, visible focus, and accessible
    form validation.
-   Use consistent loading, success, warning, empty, and error states.
-   Avoid communicating status through color alone.
-   Ensure responsive layouts for desktop, tablet, and mobile browser
    sizes.
-   Provide clear upload progress and scan-status messaging.

### 9.6 Maintainability and Quality

-   Keep API schemas and frontend types aligned.
-   Use database migrations for schema changes.
-   Test service logic, authorization boundaries, and error paths.
-   Target at least 80% test coverage for release-ready code, with a
    documented baseline during scaffolding.
-   CI should run linting, type checks, tests, frontend build,
    dependency audits, and security checks.
-   Update API and deployment documentation when behavior changes.

## 10. Proposed Information Architecture

-   **Public/auth**
    -   Sign in
    -   Verification/OTP (if enabled)
    -   Password/account recovery (if implemented)
-   **Student/Teacher**
    -   Dashboard
    -   Library browse
    -   Global search
    -   Resource detail/upload
    -   Groups and conversations
    -   Notifications
    -   Profile/settings
-   **Admin**
    -   Overview dashboard
    -   User management
    -   Academic structure
    -   Resource moderation
    -   Scan quarantine queue
    -   Teacher allowlist
    -   Audit log viewer/export
    -   System health/settings

The final navigation must be reconciled with implemented routes before
release.

## 11. High-Level Architecture

### Frontend

-   React + Vite
-   Tailwind CSS
-   React Router
-   Zustand for client state
-   TanStack Query for server state
-   Axios for API calls
-   Socket.IO Client for real-time communication
-   React Hook Form + Zod for forms and validation

### Backend

-   Flask application factory and blueprints
-   SQLAlchemy ORM
-   Alembic migrations
-   Flask-SocketIO for real-time events
-   Gunicorn for application serving
-   Celery for asynchronous and scheduled tasks

### Data and Infrastructure

-   Supabase PostgreSQL for relational data
-   Supabase Storage for uploaded files
-   Redis for caching, queues, rate limiting, and real-time coordination
    where configured
-   ClamAV or the configured scanning service for malware scanning
-   Nginx and Docker for deployment/reference infrastructure
-   Gmail SMTP for development email delivery; production email
    configuration must be reviewed

### Architectural Requirements

-   Keep business rules in service/domain layers rather than UI
    components.
-   Keep database access and permission filters in backend
    repositories/services.
-   Never rely on frontend route hiding as the sole access control.
-   Version and document API contracts.
-   Separate web requests from slow scanning/aggregation tasks.
-   Ensure socket events apply the same access rules as REST endpoints.

## 12. Data Model --- Conceptual Entities

Exact fields and relationships must follow the actual SQLAlchemy models
and Alembic migrations.

-   **User:** identity, role, active state, profile metadata,
    timestamps.
-   **Department:** top-level academic unit.
-   **Program:** belongs to a department.
-   **Semester:** belongs to a program.
-   **Section:** belongs to the relevant program/semester structure.
-   **Subject:** academic subject associated with the hierarchy.
-   **Resource:** metadata, owner/uploader, academic scope, visibility,
    publication state, storage reference, scan state, timestamps.
-   **Conversation/Group:** type, name/metadata, owner, active/archive
    state.
-   **ConversationParticipant:** membership and participant role.
-   **Message:** conversation, sender, content, timestamps, edit
    metadata.
-   **AuditLog:** actor, action, target entity, request/correlation
    identifier, metadata, timestamp; append-only.
-   **DailyStats / ChatActivity:** aggregate metrics only, without
    message/file contents.
-   **Notification / NotificationPreference:** delivery state and user
    preferences where implemented.
-   **TeacherAllowlist:** approved teacher identities/emails where the
    onboarding flow requires it.

## 13. API Requirements

The API should use a consistent versioned prefix (currently documented
as `/api/v1`) and a consistent response envelope for success and error
cases.

Expected endpoint groups include: - Authentication and current-user
identity. - Academic structure. - Library browse, resource detail,
upload, publish, download, and search. - Scan status and moderation. -
Groups, participants, conversations, messages, and real-time socket
events. - Notifications and preferences. - Admin dashboard, user
management, academic management, moderation, audit logs, and exports. -
Health checks and internal metrics.

Example search contract from the engineering plan:

`GET /api/v1/library/search?q={query}&filters={...}`

Search results must be permission-filtered before serialization. API
documentation must reflect actual routes and schemas; this PRD does not
prescribe undocumented endpoint details.

## 14. Security and Abuse Cases

The implementation and test plan must explicitly cover:

1.  A student requesting another department's private resource.
2.  A non-member attempting to read or send a group message.
3.  A regular user calling an admin endpoint directly.
4.  A user changing an object ID to access another user's resource
    (IDOR/BOLA).
5.  An uploaded file exceeding configured limits or disguising its type.
6.  A scanner timeout incorrectly resulting in a clean status.
7.  A malicious filename or metadata field attempting injection.
8.  CSV values beginning with spreadsheet formula characters.
9.  Replayed, expired, or stolen refresh credentials.
10. Repeated OTP, login, upload, search, or message requests intended to
    abuse resources.
11. A background job executing twice or being retried after partial
    failure.
12. Secrets or private content appearing in logs, client errors,
    analytics, or notifications.
13. An administrator deleting/moderating a resource without a reason or
    audit event.
14. Redis, database, storage, SMTP, or scanner outages.
15. Search snippets leaking private data or unsafe HTML.

## 15. Acceptance and Definition of Done

A feature is complete only when all applicable criteria are met:

-   Requirements and edge cases are documented.
-   Authorization is enforced on the server and tested for both allowed
    and denied cases.
-   Input validation and safe error handling are implemented.
-   Loading, success, empty, warning, and failure states are present in
    the UI.
-   Database changes include reviewed migrations and rollback
    considerations.
-   Unit/integration tests cover normal paths, boundary cases, and
    failure paths.
-   Frontend tests cover meaningful user interaction.
-   End-to-end tests cover critical user journeys.
-   Lint and type checks pass for changed code.
-   No high-severity dependency/security finding is introduced without
    an explicit, documented exception.
-   Logs do not include secrets or unnecessary personal/content data.
-   API and user-facing documentation are updated.
-   Relevant audit events and operational metrics are implemented.
-   CI is green and the change is reviewed before merging.

## 16. Release Plan

This sequence is a product-level release plan and should be aligned with
the repository's phase documents and actual completion status.

### Phase 1 --- Foundation

-   Application structure and configuration.
-   Database models and initial migration.
-   Frontend shell and route structure.
-   CI and local development setup.
-   Baseline testing and engineering documentation.

### Phase 2 --- Identity and Academic Access

-   Authentication/session lifecycle.
-   Roles and authorization policies.
-   Academic structure and teacher allowlist where required.
-   Initial user and permission management.
-   Tests for access boundaries.

### Phase 3 --- Library and File Lifecycle

-   Resource metadata and academic categorization.
-   Upload, storage, browse, download, and search foundations.
-   File scan task integration and status tracking.
-   Storage/permission security tests.

### Phase 4 --- Collaboration

-   Groups/conversations and participants.
-   Message persistence and real-time delivery.
-   Notification workflows where in scope.
-   Ownership transfer, archive, and message policy.
-   End-to-end collaboration tests.

### Phase 5 --- Administration and Production Hardening

-   Admin dashboard and aggregate analytics.
-   Audit viewer/export and moderation queue.
-   Search polish and permission-aware ranking.
-   Observability, security review, performance work, resilience,
    backups, and release candidate checks.

**Release gate:** do not declare production-ready until a fresh clone
can install, migrate, run tests, pass lint/type/build checks, and
complete the documented smoke-test and recovery procedures.

## 17. Risks, Dependencies, and Mitigations

  ----------------------------------------------------------------------------
  Risk/dependency         Impact                       Mitigation
  ----------------------- ---------------------------- -----------------------
  External                Login, upload, and download  Health checks,
  database/storage        failures                     timeouts, retry policy,
  availability                                         incident runbook

  Malware scanner         Delayed file availability or Explicit failed/pending
  unavailable or slow     safety uncertainty           state, alerting,
                                                       re-scan path; never
                                                       mark failure as clean

  Authorization defects   Data leakage or privilege    Centralized permission
                          escalation                   checks, route
                                                       enumeration tests, IDOR
                                                       tests

  Search query            Slow library discovery       Appropriate indexes,
  performance                                          query plans,
                                                       pagination, cache where
                                                       suitable

  Real-time               Delayed group updates        Reconnect behavior,
  infrastructure outage                                persisted messages,
                                                       clear degraded state

  Email delivery failure  Missed                       Bounded retries,
                          verification/notifications   delivery status, admin
                                                       visibility

  Schema drift between    Runtime errors and failed    Typed API contracts,
  backend and frontend    builds                       generated/validated
                                                       schemas where feasible,
                                                       CI checks

  Incomplete              Regressions and deployment   Stabilize fresh-clone
  test/lint/type baseline risk                         baseline before
                                                       resuming feature
                                                       expansion

  Over-collection of      Privacy and trust impact     Aggregate-only schema,
  analytics                                            data review, tests
                                                       preventing content/PII
                                                       leakage

  Backup that cannot be   Prolonged outage/data loss   Scheduled backups plus
  restored                                             documented restore
                                                       drills and row-count
                                                       validation
  ----------------------------------------------------------------------------

## 18. Open Questions

These items require product/engineering confirmation before a production
release:

1.  What institution-specific identity provider, if any, will be used?
2.  What are the exact rules for student, teacher, and administrator
    onboarding?
3.  Which file types and maximum sizes are allowed in production?
4.  Are resources public to the institution, department-scoped,
    group-scoped, or a combination?
5.  What retention and deletion policies apply to accounts, files,
    messages, audit logs, and backups?
6.  Who can publish resources, and does publication require approval?
7.  What is the intended behavior for a scan failure: block all
    downloads, allow a documented admin exception, or another policy?
8.  What are the expected user count, peak concurrent sessions, and
    storage volume?
9.  Which production hosting provider and email provider will be
    supported?
10. Which accessibility standard and browser support matrix will be used
    for acceptance?
11. What exact release gate and security review are required for the
    first production launch?
12. Which phase items are fully implemented and verified versus planned
    or partially complete?

## 19. Repository and Engineering References

Use these repository documents as implementation-level sources of truth
and keep them synchronized with the code:

-   `README.md` --- repository layout, stack, local development, and
    test commands.
-   `PHASE2_PLAN.md` --- Phase 2 implementation plan.
-   `PHASE3_PLAN.md` --- Phase 3 implementation plan.
-   `PHASE4_PLAN.md` --- Phase 4 implementation plan.
-   `PHASE5_PLAN.md` --- admin dashboard, analytics, search, and
    hardening plan.
-   `PHASE4_VERIFICATION.md` and `PHASE5_VERIFICATION.md` --- phase
    verification records.
-   `STABILIZATION_REPORT.md` and `STABILIZATION_SUMMARY.md` ---
    stabilization findings and remaining baseline work.
-   `docs/` --- detailed architecture, API, feature, performance,
    deployment, and operational documentation.

------------------------------------------------------------------------

**End of document**
