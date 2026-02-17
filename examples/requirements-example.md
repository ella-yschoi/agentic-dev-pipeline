# Requirements: User Authentication API

## Functional Requirements

### FR-1: User Registration
- **Endpoint**: `POST /auth/register`
- **Request body**: `{ "email": string, "password": string }`
- **Validation**:
  - Email must be valid format
  - Password must be >= 8 characters
  - Email must be unique (409 Conflict if duplicate)
- **Response**: `201 Created` with `{ "id": int, "email": string }`
- **Security**: Password stored as bcrypt hash

### FR-2: User Login
- **Endpoint**: `POST /auth/login`
- **Request body**: `{ "email": string, "password": string }`
- **Response**: `200 OK` with `{ "access_token": string, "token_type": "bearer" }`
- **Error**: `401 Unauthorized` if credentials invalid
- **Token**: JWT with `user_id` claim, 30-minute expiry

### FR-3: Get Current User
- **Endpoint**: `GET /auth/me`
- **Headers**: `Authorization: Bearer <token>`
- **Response**: `200 OK` with `{ "id": int, "email": string }`
- **Error**: `401 Unauthorized` if token invalid or expired

## Non-Functional Requirements

### NFR-1: Security
- Passwords MUST be bcrypt-hashed (never plaintext)
- JWT secret MUST come from environment variable `JWT_SECRET`
- Token expiry: 30 minutes

### NFR-2: Testing
- Unit tests for each endpoint (happy path + error cases)
- Test password hashing (verify hash != plaintext)
- Test token expiry handling

### NFR-3: Code Quality
- Follow existing project patterns (see `app/routers/tasks.py`)
- Type annotations on all functions
- Pydantic models for request/response schemas
