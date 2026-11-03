# Mosquitto Local Setup

**This broker is for local development only. Do NOT expose to public networks.**

## Password file setup

When running with `docker compose up`, the container will **automatically create** `/mosquitto/config/password.txt` on first launch using `MQTT_USERNAME` and `MQTT_PASSWORD` from your `.env` (default: `asd_backend` / `changeme`).

If you want to manually create or update the password file:

```bash
# From the repository root:
docker run --rm -v "$(pwd)/mosquitto/config:/mosquitto/config" \
  eclipse-mosquitto:2 \
  mosquitto_passwd -b -c /mosquitto/config/password.txt asd_backend changeme

# On Windows PowerShell:
docker run --rm -v "${PWD}/mosquitto/config:/mosquitto/config" `
  eclipse-mosquitto:2 `
  mosquitto_passwd -b -c /mosquitto/config/password.txt asd_backend changeme
```

Replace `changeme` with a local-only password. The file `mosquitto/config/password.txt`
is gitignored and must never be committed.

## Environment variables

Set `MQTT_PASSWORD` in your backend `.env` (or shell) to match the password above.

See `.env.example` for all MQTT-related variables.
