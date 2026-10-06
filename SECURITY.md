# Security

Do not publish credentials, database files, private corpus text or a working exploit containing private data in an issue. Report a sensitive vulnerability through GitHub's private vulnerability reporting when available, or contact the repository owner to arrange a private channel.

Production installations must set a fresh secret, disable debug, restrict allowed hosts, use HTTPS, secure cookies and a trusted reverse proxy, and rate-limit authentication. There is no built-in application login rate limiter; the supplied Nginx example provides it. See [deployment instructions](docs/DEPLOYMENT.md).

Backups contain corpus text, user information and password hashes. Store them outside the repository with restricted access. Application code, database backups and an OS snapshot are different recovery artifacts; restore to a trusted system after compromise.
