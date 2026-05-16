# Product

DigitalOcean-TeleBot is a Telegram bot that helps administrators manage one or more DigitalOcean accounts and their droplets directly from chat. It is sometimes referred to as "DigitalOcean Manager Bot" / "ZidStore" in user-facing copy.

## Core capabilities

- **Account management**: add DigitalOcean API tokens (with optional remarks), list saved accounts, view per-account details (email, balance, month-to-date usage, billing date), and remove accounts.
- **Batch testing**: validate every saved token in one pass and bulk-delete tokens that fail authentication.
- **Droplet provisioning**: guided flow to pick account → region → size → OS → name, then create the droplet, inject a generated root password via cloud-init `user_data`, wait for the public IP, and report it back.
- **Droplet operations**: list droplets per account, view details (status, IP, OS, region, disk, created date), rename, shutdown, reboot, power on, rebuild, reset root password, and destroy.

## Audience and access model

- Single-tenant: only Telegram user IDs listed in `config.json` `BOT.ADMINS` may interact with the bot. All other users get a fixed "tidak memiliki izin" message.
- Operator is expected to self-host (typical deployment is a `systemd` service installed by the `start` shell script).

## Language and tone

All user-facing strings (button labels, prompts, error messages, status updates) are in **Bahasa Indonesia** with light emoji decoration. Keep this consistent when adding or editing features. Internal identifiers (function names, callback paths, dict keys, comments) stay in English.

## Out of scope

- Multi-tenant / per-user account isolation (the TinyDB store is shared across all admins).
- Spaces, Kubernetes, load balancers, databases, or any DigitalOcean product beyond Droplets and account billing.
- Localization to languages other than Bahasa Indonesia.
