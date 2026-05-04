# File Management System

Full-stack file management application.

- **Backend** ([`backend/`](backend)): AWS Lambda, API Gateway, DynamoDB, S3, ElastiCache Redis, deployed with AWS SAM.
- **Frontend** ([`frontend/`](frontend)): React + TypeScript SPA built with Vite. Minimalistic, monochrome UI with light/dark theme.

## Backend Architecture

- `POST /signup` creates a user, stores a bcrypt password hash in DynamoDB, returns a JWT, and caches that JWT in Redis.
- `POST /login` validates credentials and returns a cached JWT.
- `POST /files` validates the JWT, creates a pending file metadata row, and returns a presigned S3 PUT URL.
- `GET /files` lists the caller's files from DynamoDB.
- `DELETE /files/{fileId}` deletes the caller's S3 object and DynamoDB metadata row.

Protected routes require:

```text
Authorization: Bearer <jwt>
```

## Project Layout

```text
backend/
  template.yaml
  samconfig.toml
  shared/
    requirements.txt
    python/shared/
  auth-lambda/
  upload-lambda/
  list-lambda/
  delete-lambda/
  tests/
frontend/
  package.json
  vite.config.ts
  src/
    api/
    auth/
    screens/
    utils/
```

## Prerequisites

- Python 3.11 for Lambda compatibility. The tests also pass on Python 3.12 locally.
- AWS SAM CLI.
- AWS CLI configured for the target account.
- An existing VPC with at least two private subnets.
- The private route table IDs for those subnets.

## Local Tests

Install test dependencies:

```bash
cd backend
python -m pip install -r requirements-dev.txt
```

Run the test suite:

```bash
python -m pytest
```

The tests use `moto` for DynamoDB/S3 and `fakeredis` for the JWT cache, so they do not call AWS.

## Build

```bash
cd backend
sam build
```

## Deploy

Use a 32+ character JWT secret and pass your VPC values:

```bash
cd backend
sam deploy \
  --parameter-overrides \
    JwtSecret="replace-with-a-strong-32-char-minimum-secret" \
    VpcId="vpc-xxxxxxxx" \
    PrivateSubnetIds="subnet-aaaaaaaa,subnet-bbbbbbbb" \
    RouteTableIds="rtb-aaaaaaaa,rtb-bbbbbbbb" \
    AllowedOrigins="*" \
    MaxUploadBytes="52428800"
```

The GitHub Actions deploy workflow requires `AWS_ACCESS_KEY_ID`,
`AWS_SECRET_ACCESS_KEY`, and `JWT_SECRET` as repository secrets. `JWT_SECRET`
must be at least 32 characters. Non-secret deployment settings such as
`AWS_REGION`, `VPC_ID`, `PRIVATE_SUBNET_IDS`, `ROUTE_TABLE_IDS`,
`ALLOWED_ORIGINS`, and `MAX_UPLOAD_BYTES` can be set as repository variables.

Useful SAM outputs:

- `ApiUrl`: API Gateway base URL.
- `FileBucketName`: private S3 bucket for uploaded files.
- `UsersTableName`: DynamoDB users table.
- `FilesTableName`: DynamoDB files table.
- `RedisEndpoint`: Redis host and port used for cached JWT allow-list checks.

## API Examples

Signup:

```bash
curl -X POST "$API_URL/signup" \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password123"}'
```

Request an upload URL:

```bash
curl -X POST "$API_URL/files" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"fileName":"test.txt","contentType":"text/plain","size":12}'
```

Upload directly to S3 with the returned URL:

```bash
curl -X PUT "$UPLOAD_URL" \
  -H "Content-Type: text/plain" \
  --data-binary "@test.txt"
```

## Frontend

```bash
cd frontend
npm install
cp .env.example .env
# Set VITE_API_URL in .env to the SAM stack's ApiUrl output.
npm run dev
```

See [`frontend/README.md`](frontend/README.md) for full details on routes,
build/deploy, and configuration.
