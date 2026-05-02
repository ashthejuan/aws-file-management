# File Management Frontend

Minimal React + TypeScript SPA that talks to the SAM backend in [`../backend`](../backend).

## Stack

- React 18 + TypeScript
- Vite for dev/build
- React Router for routing
- Plain CSS, monochrome palette, automatic light/dark via `prefers-color-scheme`

## Screens

| Route       | Screen     | Backend calls                                            |
| ----------- | ---------- | -------------------------------------------------------- |
| `/login`    | Sign in    | `POST /login`                                            |
| `/signup`   | Sign up    | `POST /signup`                                           |
| `/`         | Dashboard  | `GET /files`, `POST /files`, S3 `PUT`, `DELETE /files/{fileId}` |

The dashboard handles the full upload flow:

1. `POST /files` to obtain a presigned S3 PUT URL.
2. `PUT` the file directly to S3 with the required `Content-Type` header.
3. Refresh the file list.

The auth token is stored in `localStorage` keyed at `fm.auth` and is cleared automatically when it expires. A `401` from any API call also clears the session and bounces back to `/login`.

## Setup

```bash
cd frontend
npm install
cp .env.example .env
# Edit .env and set VITE_API_URL to the SAM stack's ApiUrl output.
```

## Run locally

```bash
npm run dev
```

Open http://localhost:5173.

## Build

```bash
npm run build
npm run preview   # optional: serve the built app
```

The static bundle lands in `dist/`. Host it anywhere (S3 + CloudFront, Vercel, Netlify, GitHub Pages, …).

## Configuration

| Variable        | Description                                                                 |
| --------------- | --------------------------------------------------------------------------- |
| `VITE_API_URL`  | Base URL of the deployed API Gateway stage. The trailing slash is optional. |

## CORS note

Browser uploads PUT directly to S3 with the presigned URL. The `template.yaml`
already configures S3 CORS via the `AllowedOrigin` parameter. When you deploy
the frontend to a real domain, redeploy the SAM stack with
`AllowedOrigin=https://your-frontend-domain` so both the API Gateway and bucket
allow it.
