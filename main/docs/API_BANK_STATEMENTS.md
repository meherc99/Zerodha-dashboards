# Bank Statement Upload API

## Overview
API endpoints for uploading and managing PDF bank statements.

## Authentication
All endpoints require JWT authentication via `Authorization: Bearer <token>` header.

## Endpoints

### 1. Upload Bank Statement
**POST** `/api/bank-accounts/:account_id/statements/upload`

Upload a PDF bank statement for a specific bank account.

**Request:**
- Content-Type: `multipart/form-data`
- Body: `file` - PDF file (max 10MB)

**Response:**
- **202 Accepted** - Statement uploaded successfully
  ```json
  {
    "statement_id": 1,
    "message": "Statement uploaded successfully",
    "status": "uploaded"
  }
  ```
- **400 Bad Request** - Validation error (invalid file type, too large, etc.)
- **404 Not Found** - Bank account not found or doesn't belong to user
- **401 Unauthorized** - Missing or invalid JWT token

**Validation:**
- Only PDF files allowed (`.pdf` extension)
- Maximum file size: 10 MB
- File must not be empty
- Account must belong to authenticated user

**File Storage:**
- Path: `backend/uploads/bank_statements/{user_id}/{account_id}/{uuid}.pdf`
- Filename: UUID-based for uniqueness and security

---

### 2. List Statements for Account
**GET** `/api/bank-accounts/:account_id/statements`

Get all statements for a specific bank account.

**Response:**
- **200 OK** - List of statements
  ```json
  [
    {
      "id": 1,
      "bank_account_id": 1,
      "statement_period_start": "2024-01-01",
      "statement_period_end": "2024-01-31",
      "pdf_file_path": "/path/to/file.pdf",
      "upload_date": "2024-03-26T14:23:36.000Z",
      "status": "uploaded",
      "created_at": "2024-03-26T14:23:36.000Z"
    }
  ]
  ```
- **404 Not Found** - Bank account not found or doesn't belong to user
- **401 Unauthorized** - Missing or invalid JWT token

---

### 3. Get Statement Details
**GET** `/api/statements/:statement_id`

Get details of a specific statement.

**Response:**
- **200 OK** - Statement details
  ```json
  {
    "id": 1,
    "bank_account_id": 1,
    "statement_period_start": "2024-01-01",
    "statement_period_end": "2024-01-31",
    "pdf_file_path": "/path/to/file.pdf",
    "upload_date": "2024-03-26T14:23:36.000Z",
    "parsing_template_id": null,
    "status": "uploaded",
    "error_message": null,
    "parsed_data": null,
    "created_at": "2024-03-26T14:23:36.000Z"
  }
  ```
- **404 Not Found** - Statement not found or doesn't belong to user
- **401 Unauthorized** - Missing or invalid JWT token

---

### 4. Delete Statement
**DELETE** `/api/statements/:statement_id`

Delete a statement and its associated PDF file.

**Response:**
- **200 OK** - Statement deleted successfully
  ```json
  {
    "message": "Statement deleted successfully"
  }
  ```
- **404 Not Found** - Statement not found or doesn't belong to user
- **401 Unauthorized** - Missing or invalid JWT token

**Behavior:**
- Deletes database record
- Deletes PDF file from disk
- Cleans up empty directories

---

## Status Values
- `uploaded` - Initial status after upload
- `parsing` - (Future) Being parsed
- `review` - (Future) Parsed data awaiting review
- `approved` - (Future) Reviewed and approved
- `failed` - (Future) Parsing failed

## Security
- All endpoints verify user ownership through bank_account relationship
- Returns 404 (not 403) for unauthorized access to prevent information disclosure
- File paths use UUID to prevent enumeration attacks
- Secure filename sanitization using `werkzeug.utils.secure_filename`

## Error Handling
- Validation errors: 400 Bad Request with descriptive error message
- Not found: 404 Not Found
- Server errors: 500 Internal Server Error
- Failed uploads trigger automatic file cleanup

## Testing
Run tests with:
```bash
pytest tests/test_bank_statement_routes.py -v
```

21 tests covering:
- Valid and invalid uploads
- File type and size validation
- Ownership verification
- Authentication requirements
- CRUD operations
