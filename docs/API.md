# API Reference (starter)

Base path: `/api`

## Auth
- `POST /api/auth/register` JSON {name,email,password,role} -> {ok, unique_id}
- `POST /api/auth/login` JSON {email,password} -> {ok, unique_id, role, name}

## Uploads
- `GET /api/uploads` -> list of uploads
- `POST /api/uploads` multipart/form-data file + title + optional faculty_unique_id -> {ok,id,filename}

## Notices
- `GET /api/notices` -> list of notices

## Complaints
- `POST /api/complaints` JSON {subject,message,sender_unique_id?}
- `GET /api/complaints` -> list (admin)

## Chat
- `GET /api/chat/history` -> chat messages (global)
- `POST /api/chat/send` JSON {to_unique_id?, message, context_type, context_id, sender_unique_id?}
