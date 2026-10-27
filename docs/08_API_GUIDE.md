
# API Guide

## Principles
- RESTful endpoints
- Version all APIs (`/api/v1`)
- Stateless authentication with JWT
- JSON request/response only
- Consistent error format

## Response Format
```json
{
  "success": true,
  "message": "Operation completed.",
  "data": {}
}
```

## Error Format
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input."
  }
}
```

## Standards
- Pagination
- Filtering
- Sorting
- Search
- Rate limiting
- Idempotency where applicable
- OpenAPI/Swagger documentation
