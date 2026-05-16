# Tech Stack

## Language and runtime

- **Python 3** (the install script targets system `python3` / `pip3`; no venv is used in the documented flow).
- Pinned dependencies in `requirements.txt`:
  - `pyTelegramBotAPI==3.8.2` — Telegram Bot framework (`telebot`).
  - `python-digitalocean==1.16.0` — DigitalOcean API client (`digitalocean`).
  - `tinydb==4.5.1` — file-backed JSON document DB (`db.json`).
  - `requests==2.26.0` — used directly for the rename droplet call (the v1.16 client does not expose it).
  - `jsonpickle`, `certifi`, `charset-normalizer`, `idna`, `urllib3` — transitive / utility deps.

When adding new dependencies, pin them with `==` to match the existing style.

## Configuration

- All runtime config comes from `config.json` at the repo root, loaded by `main.parse_config()` and then exported into `os.environ`:
  - `BOT.NAME` → `bot_name`
  - `BOT.TOKEN` → `bot_token`
  - `BOT.ADMINS` → `bot_admins` (JSON-encoded list of integer Telegram user IDs)
- Modules read these via `os.environ.get(...)`. Do not read `config.json` directly outside of `main.py`.
- `config.json` contains a real bot token and admin ID in this repo. Treat it as a secret: do not log it, echo it back in chat, or commit changes that expose new tokens.

## Persistence

- TinyDB at `db.json` (created on first write, gitignored expected). Single table: `Accounts` with fields `email`, `token`, `remarks`, `date`. Records are addressed by TinyDB `doc_id`.
- All DB access goes through `utils.db.AccountsDB`. Add new persistence concerns there rather than instantiating TinyDB elsewhere.

## Telegram conventions

- Single global bot instance is created in `_bot.py` and imported as `from _bot import bot` everywhere. Do not construct additional `TeleBot` instances.
- All messages are sent with `parse_mode='HTML'`. Stick to `<b>`, `<code>`, `<a>` tags and escape user-supplied content that could break HTML.
- Multi-step flows use `bot.register_next_step_handler(msg, handler)` for free-text input, and inline keyboards for option selection.
- Callback data uses a URL-style scheme parsed in `bot.py`: `func_name?key=value&key2=value2`. The path resolves to a function in module globals; the query becomes a `dict[str, list[str]]` (always index `[0]` to read a single value). When adding new callback targets, export them via `modules/__init__.py` so they appear in `globals()`.
- Sub-router pattern: `create_droplet` uses a `nf` (next function) query param to dispatch within a single top-level callback name. Reuse this pattern for other multi-step wizards.

## DigitalOcean access

- Prefer the `digitalocean` package (`Manager`, `Account`, `Balance`, `Droplet`) for new work.
- Direct `requests` calls to `https://api.digitalocean.com/v2/...` are acceptable when the client library lacks the endpoint (see `rename_droplet.py` for the pattern: `Authorization: Bearer <token>`, JSON body, check `status_code == 201` for action endpoints).
- New droplets get their root password set via the cloud-init script in `utils.set_root_password_script.set_root_password_script(password)`. Passwords come from `utils.password_generator.password_generator()`.

## Logging and errors

- Use `telebot.logger` (already configured to `INFO` in `bot.py`). Avoid `print()` in module code.
- Top-level handlers in `bot.py` catch all exceptions, `traceback.print_exc()` to stdout, and reply to the user with the exception text. Inside modules, prefer to catch the specific exception, edit the in-flight message with a Bahasa Indonesia error string, and `return`. Don't let an exception bubble up after a long-running side effect (e.g. droplet already created) without informing the user.

## Common commands

Install dependencies:

```
pip install -r requirements.txt
```

Run locally (Windows / cross-platform):

```
python main.py
```

Provision on a fresh Linux box (interactive — prompts for token, admin ID, store name, writes a `do.service` systemd unit):

```
chmod +x start && ./start
```

There is no test suite, linter, or formatter configured. If you add tooling, document it here.
