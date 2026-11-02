# Run with a new Firebase project

## 1. Create a new project

In Firebase Console, create a new project that is only for this portfolio application. Do not use the recovered project.

Enable these services:

1. Authentication → Sign-in method → Email/Password.
2. Firestore Database → create a Native-mode database.

Create a test user in Authentication after the app starts, then use that account at the login page.

## 2. Create fresh runtime files

Copy the examples without overwriting them:

    Copy-Item secrets/firebase-web-config.example.json secrets/firebase-web-config.json
    Copy-Item secrets/firebase-service-account.example.json secrets/firebase-service-account.json
    Copy-Item .env.example .env

From Firebase project settings, add a Web app and place its configuration values in `secrets/firebase-web-config.json`.

From Google Cloud IAM → Service Accounts, create a dedicated service account for this portfolio application with only the Firestore permissions it needs. Generate a new JSON key and save it only as `secrets/firebase-service-account.json`.

Generate the Flask secret, then replace the value in `.env`:

    python -c "import secrets; print(secrets.token_urlsafe(48))"

The three files above are ignored by Git and excluded from Docker builds. Docker Compose mounts `secrets/` read-only when the container starts.

## 3. Start locally

    docker compose up --build

Visit http://localhost:8080 and sign in with the Firebase test user. This creates data only in the new Firebase project.

## AWS runtime configuration

For an AWS container deployment, store these three values in AWS Secrets Manager:

- `FLASK_SECRET_KEY`
- `FIREBASE_WEB_CONFIG_JSON` — complete contents of the new web configuration JSON
- `FIREBASE_SERVICE_ACCOUNT_JSON` — complete contents of the new service-account JSON

Inject them as runtime environment variables in the container service. Do not place them in the Dockerfile, a GitHub Action variable, an image layer, or an ECR repository. The application accepts the JSON environment-variable form in AWS and the mounted-file form locally.

## Before publishing

Run this from the repository root and confirm it returns no unexpected files:

    git status --ignored
    git grep -nEi "private_key|client_secret|AIza[0-9A-Za-z_-]{20,}|serviceAccount.json|fbconfig.json"

An example file may contain placeholder names, but it must never contain a real project ID, API key, email address, key ID, or private key.
