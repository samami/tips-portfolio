# Security boundary

This project may be published only after a clean credential scan. The historical archive itself must remain private because it contained a Firebase service-account key.

## Runtime rules

- Create a new Firebase project and service account. Never reuse the recovered project or key.
- Keep `SESSION_COOKIE_SECURE=true` in any HTTPS deployment.
- Store `FLASK_SECRET_KEY` and the new Firebase service-account JSON in a runtime secret manager, not the repository or Docker image.
- Grant the new service account only the Firestore permissions the app needs.
- Use Firebase Authentication's Email/Password provider only with test/portfolio accounts.

## Before a public production deployment

The recovered app was a small internal-style application. Add CSRF protection and rate limiting before accepting real user data or exposing it to untrusted users. For a portfolio demonstration, use fictional staff, client, and tip records only.
