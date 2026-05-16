import re

from telebot.types import (
    CallbackQuery,
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

import digitalocean
import requests

from _bot import bot
from utils.db import AccountsDB

# Per-user rename state. Keyed by Telegram user id.
rename_states = {}

# DigitalOcean droplet name: letters, digits, and hyphens only.
# 3-63 chars, must start and end with an alphanumeric character.
_NAME_RE = re.compile(r'^[a-zA-Z0-9](?:[a-zA-Z0-9-]{1,61}[a-zA-Z0-9])?$')


def _clear_state(user_id: int):
    rename_states.pop(user_id, None)


def rename_droplet(call: CallbackQuery, data: dict):
    """Entry point for the rename flow (triggered from droplet_detail)."""
    doc_id = data['doc_id'][0]
    droplet_id = data['droplet_id'][0]

    try:
        account = AccountsDB().get(doc_id=doc_id)
        droplet = digitalocean.Droplet().get_object(
            api_token=account['token'],
            droplet_id=droplet_id
        )
    except Exception as e:
        bot.edit_message_text(
            text=f'⚠️ Kesalahan saat mengambil akun atau droplet: <code>{str(e)}</code>',
            chat_id=call.from_user.id,
            message_id=call.message.message_id,
            parse_mode='HTML'
        )
        return

    rename_states[call.from_user.id] = {
        'doc_id': doc_id,
        'droplet_id': droplet_id,
        'current_name': droplet.name,
    }

    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton(
            text='🔙 Batal',
            callback_data=f'cancel_rename?doc_id={doc_id}&droplet_id={droplet_id}'
        )
    )

    bot.edit_message_text(
        text=f'<b>✏️ Rename Droplet</b>\n\n'
             f'🏷️ Nama saat ini: <code>{droplet.name}</code>\n\n'
             '📝 Silakan kirim nama baru untuk droplet ini.\n'
             'Nama harus 3-63 karakter dan hanya boleh mengandung huruf, angka, '
             'dan tanda hubung. Tidak boleh diawali atau diakhiri tanda hubung.\n\n'
             '/cancel untuk membatalkan',
        chat_id=call.from_user.id,
        message_id=call.message.message_id,
        parse_mode='HTML',
        reply_markup=markup
    )


def handle_rename_input(message: Message) -> bool:
    """Called from the global text_handler. Returns True if the message was consumed."""
    user_id = message.from_user.id
    state = rename_states.get(user_id)
    if state is None:
        return False

    text = (message.text or '').strip()

    if text == '/cancel':
        _clear_state(user_id)
        bot.reply_to(message, '❌ Rename dibatalkan.')
        return True

    if not _NAME_RE.match(text):
        bot.reply_to(
            message,
            '❌ Nama tidak valid. Gunakan 3-63 karakter (huruf, angka, tanda hubung) '
            'dan jangan diawali/diakhiri tanda hubung. Silakan coba lagi atau /cancel.'
        )
        return True

    doc_id = state['doc_id']
    droplet_id = state['droplet_id']
    current_name = state['current_name']

    try:
        account = AccountsDB().get(doc_id=doc_id)
    except Exception as e:
        _clear_state(user_id)
        bot.reply_to(
            message,
            f'⚠️ Kesalahan saat mengambil akun: <code>{str(e)}</code>',
            parse_mode='HTML'
        )
        return True

    processing_msg = bot.reply_to(message, '🔄 Sedang mengubah nama droplet...')

    try:
        response = requests.post(
            f'https://api.digitalocean.com/v2/droplets/{droplet_id}/actions',
            headers={
                'Authorization': f'Bearer {account["token"]}',
                'Content-Type': 'application/json',
            },
            json={'type': 'rename', 'name': text},
            timeout=30
        )

        if response.status_code == 201:
            bot.edit_message_text(
                text=f'✅ <b>Nama droplet berhasil diubah</b>\n\n'
                     f'🏷️ Nama lama: <code>{current_name}</code>\n'
                     f'🏷️ Nama baru: <code>{text}</code>',
                chat_id=message.chat.id,
                message_id=processing_msg.message_id,
                parse_mode='HTML'
            )
        else:
            try:
                error_message = response.json().get('message', f'HTTP {response.status_code}')
            except ValueError:
                error_message = f'HTTP {response.status_code}: {response.text[:100]}'

            bot.edit_message_text(
                text=f'❌ <b>Gagal mengubah nama droplet</b>\n\n'
                     f'Error: <code>{error_message}</code>',
                chat_id=message.chat.id,
                message_id=processing_msg.message_id,
                parse_mode='HTML'
            )
    except Exception as e:
        bot.edit_message_text(
            text=f'❌ <b>Gagal mengubah nama droplet</b>\n\n'
                 f'Error: <code>{str(e)}</code>',
            chat_id=message.chat.id,
            message_id=processing_msg.message_id,
            parse_mode='HTML'
        )
    finally:
        _clear_state(user_id)

    return True


def cancel_rename(call: CallbackQuery, data: dict):
    """Cancel the rename flow and go back to droplet detail."""
    _clear_state(call.from_user.id)

    # Re-render the droplet detail screen (in-place edit of the same message).
    from modules.droplet_detail import droplet_detail
    droplet_detail(call, data)
