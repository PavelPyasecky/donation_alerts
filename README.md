# donation_alerts

## Local
```bash
docker compose up -d --build
docker compose down
```

## Server
1. Clone the repository on both target hosts.
2. Create `.env` from `.env.example`.
3. Keep the branch checkout aligned with the target environment:
   - `main` on prod
   - `dev` on dev
4. Log in to `a2413b08-pandasway.registry.twcstorage.ru` on the server.
5. Start the stack:

```bash
docker compose up -d rabbitmq api caddy watchtower
```

## Gitea CI/CD
- CI runs on `pull_request` and `push` for `main` and `dev`.
- CD runs on `push` and `workflow_dispatch` for `main` and `dev`.
- `main` publishes `a2413b08-pandasway.registry.twcstorage.ru/pandas-way-core/donation_alerts-app:*`.
- `dev` publishes `a2413b08-pandasway.registry.twcstorage.ru/pandas-way-core/dev/donation_alerts-app:*`.
- Each image push publishes `latest`, the bumped `VERSION`, and the commit SHA tag.
- CD updates the matching branch checkout on the target host and then runs `bash deploy.sh`.

Required Gitea secret:
```text
TIMEWEB_REGISTRY_TOKEN
DEPLOY_HOST_PROD
DEPLOY_HOST_DEV
DEPLOY_USER_PROD
DEPLOY_USER_DEV
DEPLOY_SSH_KEY_PROD
DEPLOY_SSH_KEY_DEV
DEPLOY_KNOWN_HOSTS_PROD   # optional
DEPLOY_KNOWN_HOSTS_DEV    # optional
```

Required Gitea variables:
```text
DEPLOY_PATH_PROD
DEPLOY_PATH_DEV
```
