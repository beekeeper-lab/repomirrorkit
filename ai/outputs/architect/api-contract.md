# API Contract: [API / Service Name]

## Metadata

| Field         | Value                          |
|---------------|--------------------------------|
| Date          | YYYY-MM-DD                     |
| Owner         | [API owner name or team]       |
| Related links | [Design spec / ADR / repo links] |
| Status        | Draft / Reviewed / Approved    |

*Defines the contract between this API and its consumers. All changes to this document should go through the breaking change policy below.*

---

## Endpoint Overview

| Method | Path                  | Description                    | Auth Required |
|--------|-----------------------|--------------------------------|---------------|
| [GET]  | [/api/v1/resources]   | [List resources with filtering]| [Yes]         |
| [GET]  | [/api/v1/resources/:id]| [Get a single resource by ID] | [Yes]         |
| [POST] | [/api/v1/resources]   | [Create a new resource]        | [Yes]         |
| [PUT]  | [/api/v1/resources/:id]| [Replace a resource]          | [Yes]         |
| [DELETE]| [/api/v1/resources/:id]| [Delete a resource]           | [Yes]         |

---

## Authentication and Authorization

*Describe how consumers authenticate and what permissions are required.*

- **Authentication method:** [e.g., Bearer token via OAuth 2.0 / API key / mTLS]
- **Token source:** [e.g., Organization identity provider at /oauth/token]
- **Required scopes/roles:**

| Endpoint Pattern       | Required Scope / Role          |
|------------------------|--------------------------------|
| [GET /resources]       | [read:resources]               |
| [POST /resources]      | [write:resources]              |
| [DELETE /resources/:id]| [admin:resources]              |

---

## Request and Response Schemas

### [GET /api/v1/resources]

**Query Parameters:**

| Parameter | Type    | Required | Description                    |
|-----------|---------|----------|--------------------------------|
| [page]    | [int]   | [No]     | [Page number, default 1]       |
| [limit]   | [int]   | [No]     | [Items per page, default 20]   |
| [filter]  | [string]| [No]     | [Filter expression]            |

**Response (200):**

```json
{
  "data": [
    {
      "id": "[resource-uuid]",
      "name": "[resource name]",
      "created_at": "[ISO 8601 timestamp]",
      "updated_at": "[ISO 8601 timestamp]"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": "[total count]"
  }
}
```

### [POST /api/v1/resources]

**Request Body:**

```json
{
  "name": "[resource name]",
  "description": "[optional description]",
  "properties": {
    "[key]": "[value]"
  }
}
```

**Response (201):**

```json
{
  "id": "[resource-uuid]",
  "name": "[resource name]",
  "description": "[optional description]",
  "properties": {
    "[key]": "[value]"
  },
  "created_at": "[ISO 8601 timestamp]"
}
```

---

## Error Response Format

*All errors follow this standard structure.*

```json
{
  "error": {
    "code": "[ERROR_CODE]",
    "message": "[Human-readable description]",
    "details": [
      {
        "field": "[field name if applicable]",
        "reason": "[Specific validation or processing failure]"
      }
    ],
    "trace_id": "[request trace identifier]"
  }
}
```

**Standard Error Codes:**

| HTTP Status | Code                  | Meaning                           |
|-------------|-----------------------|-----------------------------------|
| 400         | [VALIDATION_ERROR]    | [Request body or params invalid]  |
| 401         | [UNAUTHORIZED]        | [Missing or invalid credentials]  |
| 403         | [FORBIDDEN]           | [Valid credentials, insufficient permissions] |
| 404         | [NOT_FOUND]           | [Resource does not exist]         |
| 409         | [CONFLICT]            | [State conflict, e.g., duplicate] |
| 429         | [RATE_LIMITED]        | [Too many requests]               |
| 500         | [INTERNAL_ERROR]      | [Unexpected server error]         |

---

## Rate Limits

| Scope              | Limit                          | Window       |
|--------------------|--------------------------------|--------------|
| [Per consumer]     | [e.g., 1,000 requests]        | [per minute] |
| [Per IP address]   | [e.g., 100 requests]          | [per minute] |

*Rate limit headers returned: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`.*

---

## Versioning Strategy

- **Scheme:** [e.g., URI path versioning (/api/v1/...) / header-based / query param]
- **Current version:** [v1]
- **Supported versions:** [v1]
- **Sunset policy:** [e.g., Previous versions supported for 6 months after new version release]

---

## Breaking Change Policy

*A breaking change is any change that could cause existing consumers to fail.*

- [ ] Field removal or rename in response body
- [ ] New required field in request body
- [ ] Changed authentication requirements
- [ ] Changed error codes for existing scenarios
- [ ] URL path changes

**Process for breaking changes:**

1. [Announce via changelog and direct consumer notification]
2. [Provide migration guide]
3. [Support old version for deprecation period]
4. [Remove old version after sunset date]

---

## Definition of Done

- [ ] All endpoints are listed with method, path, description, and auth
- [ ] Authentication and authorization requirements are specified
- [ ] Request and response schemas include example JSON
- [ ] Error format is documented with all standard error codes
- [ ] Rate limits are defined per scope
- [ ] Versioning scheme and sunset policy are stated
- [ ] Breaking change policy is documented and agreed upon with consumers
