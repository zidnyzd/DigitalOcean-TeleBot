# Project Structure

## Layout

```
DigitalOcean-TeleBot/
├── main.py                 # Entry point: loads config.json into env, then starts polling
├── bot.py                  # Telegram message + callback dispatchers, admin gate, command map
├── _bot.py                 # Constructs the singleton telebot.TeleBot from $bot_token
├── config.json             # Runtime config: BOT.NAME, BOT.TOKEN, BOT.ADMINS (secret)
├── requirements.txt        # Pinned dependencies
├── start                   # Bash installer: prompts for config, installs deps, registers systemd unit
├── README.MD               # User-facing docs (Bahasa Indonesia)
├── db.json                 # TinyDB store (created at runtime, not in repo)
├── modules/                # One file per feature; each exposes a top-level handler function
│   ├── __init__.py         # Re-exports every handler so `from modules import *` populates globals
│   ├── start.py            # /start landing screen
│   ├── add_account.py      # Add DO API token(s) flow
│   ├── manage_accounts.py  # List saved accounts
│   ├── account_detail.py   # Per-account view + balance
│   ├── delete_account.py   # Remove a saved account
│   ├── batch_test_accounts.py        # Validate every saved token
│   ├── batch_test_delete_accounts.py # Bulk-delete invalid tokens
│   ├── manage_droplets.py  # Pick account whose droplets to manage
│   ├── list_droplets.py    # List droplets for an account
│   ├── droplet_detail.py   # Per-droplet view + action buttons
│   ├── droplet_actions.py  # delete / shutdown / reboot / power_on / rebuild / reset_password
│   ├── create_droplet.py   # Multi-step droplet creation wizard (uses `nf` sub-router)
│   └── rename_droplet.py   # Rename flow (free-text input, raw requests call)
└── utils/
    ├── db.py                       # AccountsDB wrapper around TinyDB
    ├── localizer.py                # Region slug → human name
    ├── password_generator.py       # Random root password generator
    └── set_root_password_script.py # cloud-init bash for new droplets
```

## Module conventions

Every feature module follows the same shape, and new modules should match it:

1. Imports grouped as: stdlib, then `telebot.types`, then `digitalocean`, then local `_bot` / `utils` / sibling modules.
2. The public entry point is a function with the **same name as the module file** (e.g. `manage_accounts.py` exposes `manage_accounts`). It accepts either a `Message`, a `CallbackQuery`, or `Union[Message, CallbackQuery]`.
3. If the handler is invoked from a callback that carries query params, its second argument is `data: dict` (TinyDB `doc_id`, droplet IDs, etc., always read as `data['key'][0]`).
4. Every public entry point must be re-exported from `modules/__init__.py` so the dispatcher in `bot.py` can find it via `globals()`.
5. Long-running operations should:
   - Send (or edit to) a "🔄 ..." progress message first.
   - Wrap the DO/API call in `try/except`, edit that message to a "⚠️ Kesalahan ..." string on failure, and `return`.
   - On success, edit the same message to a final "✅ ..." state with any follow-up keyboard.

## Where to put what

- **New top-level user command** (e.g. `/foo`): add the module under `modules/`, export it in `modules/__init__.py`, and add a `'/foo': 'module_name'` entry to `command_dict` in `bot.py`.
- **New inline-button action**: pick a target callback function (existing module or new), add a button whose `callback_data` is `func_name?key=value&...`, and ensure `func_name` is in `globals()` via the modules package re-export.
- **New multi-step wizard**: model it on `create_droplet.py` — one top-level entry function that dispatches by `nf` query param into private step functions in the same file. Stash per-user state in a module-level `user_dict` keyed by `from_user.id`.
- **Free-text input mid-flow**: prefer `bot.register_next_step_handler(msg, handler)` (used by `add_account`, `create_droplet`). Persistent text input that survives the next-step queue (like rename) goes through a module-level state dict checked from the global `text_handler` in `bot.py` — keep that pattern rare; if you add another, follow the `rename_droplet.handle_rename_input` shape.
- **New persistence**: extend `utils/db.py` with a new TinyDB table or a new `*DB` class. Don't open `TinyDB('db.json')` from feature modules.
- **New shared helper** (region maps, password / cloud-init builders, formatters): add to `utils/` and import from there.

## Naming and style

- File names, function names, dict keys, and callback paths are `snake_case` English.
- All chat-visible strings are in Bahasa Indonesia (see `product.md`).
- Telegram messages: open with a `<b>Title</b>` line, follow with `<code>...</code>` for any value the user might want to copy (emails, tokens, IPs, slugs), and prefix lines with a relevant emoji (👤 account, 🌍 region, 📏 size, 🖼️ OS, 🏷️ name, 🌐 IP, 🔑 password/token, 📊 status, 📅 date).
- Keep modules flat — no subpackages under `modules/` unless a feature genuinely needs multiple files.
