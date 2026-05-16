from telebot.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

import digitalocean

from _bot import bot
from utils.db import AccountsDB


def droplet_actions(call: CallbackQuery, data: dict):
    doc_id = data['doc_id'][0]
    droplet_id = data['droplet_id'][0]
    action = data['a'][0]

    try:
        account = AccountsDB().get(doc_id=doc_id)
        droplet = digitalocean.Droplet(
            token=account['token'],
            id=droplet_id
        )
    except Exception as e:
        bot.edit_message_text(
            text=f'⚠️ Kesalahan saat mengambil akun atau droplet: <code>{str(e)}</code>',
            chat_id=call.from_user.id,
            message_id=call.message.message_id,
            parse_mode='HTML'
        )
        return

    if action in globals():
        # Pass doc_id/droplet_id along so handlers can build callback_data.
        globals()[action](call, droplet, doc_id, droplet_id)


def delete(call: CallbackQuery, droplet: digitalocean.Droplet, doc_id: str, droplet_id: str):
    """Stage 1: ask for confirmation before destroying the droplet."""
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton(
            text='✅ Ya, hapus',
            callback_data=f'droplet_actions?doc_id={doc_id}&droplet_id={droplet_id}&a=confirm_delete'
        ),
        InlineKeyboardButton(
            text='🔙 Batal',
            callback_data=f'droplet_detail?doc_id={doc_id}&droplet_id={droplet_id}'
        ),
    )
    bot.edit_message_text(
        text=f'{call.message.html_text}\n\n'
             '<b>⚠️ Yakin ingin menghapus droplet ini?</b>\n'
             'Tindakan ini tidak bisa dibatalkan.',
        chat_id=call.from_user.id,
        message_id=call.message.message_id,
        reply_markup=markup,
        parse_mode='HTML'
    )


def confirm_delete(call: CallbackQuery, droplet: digitalocean.Droplet, doc_id: str, droplet_id: str):
    bot.edit_message_text(
        text=f'{call.message.html_text}\n\n'
             '<b>🔄 Menghapus droplet...</b>',
        chat_id=call.from_user.id,
        message_id=call.message.message_id,
        parse_mode='HTML'
    )

    try:
        droplet.load()
        droplet.destroy()
    except Exception as e:
        bot.edit_message_text(
            text=f'⚠️ Kesalahan saat menghapus droplet: <code>{str(e)}</code>',
            chat_id=call.from_user.id,
            message_id=call.message.message_id,
            parse_mode='HTML'
        )
        return

    bot.edit_message_text(
        text=f'{call.message.html_text}\n\n'
             f'<b>✅ Droplet telah dihapus</b>',
        chat_id=call.from_user.id,
        message_id=call.message.message_id,
        parse_mode='HTML'
    )


def shutdown(call: CallbackQuery, droplet: digitalocean.Droplet, doc_id: str, droplet_id: str):
    bot.edit_message_text(
        text=f'{call.message.html_text}\n\n'
             '<b>🔄 Mematikan droplet, silakan segarkan nanti</b>',
        chat_id=call.from_user.id,
        message_id=call.message.message_id,
        reply_markup=call.message.reply_markup,
        parse_mode='HTML'
    )

    try:
        droplet.load()
        droplet.shutdown()
    except Exception as e:
        bot.edit_message_text(
            text=f'⚠️ Kesalahan saat mematikan droplet: <code>{str(e)}</code>',
            chat_id=call.from_user.id,
            message_id=call.message.message_id,
            parse_mode='HTML'
        )


def reboot(call: CallbackQuery, droplet: digitalocean.Droplet, doc_id: str, droplet_id: str):
    bot.edit_message_text(
        text=f'{call.message.html_text}\n\n'
             '<b>🔄 Merestart droplet, silakan segarkan nanti</b>',
        chat_id=call.from_user.id,
        message_id=call.message.message_id,
        reply_markup=call.message.reply_markup,
        parse_mode='HTML'
    )

    try:
        droplet.load()
        droplet.reboot()
    except Exception as e:
        bot.edit_message_text(
            text=f'⚠️ Kesalahan saat merestart droplet: <code>{str(e)}</code>',
            chat_id=call.from_user.id,
            message_id=call.message.message_id,
            parse_mode='HTML'
        )


def power_on(call: CallbackQuery, droplet: digitalocean.Droplet, doc_id: str, droplet_id: str):
    bot.edit_message_text(
        text=f'{call.message.html_text}\n\n'
             '<b>🔄 Menyalakan droplet, silakan segarkan nanti</b>',
        chat_id=call.from_user.id,
        message_id=call.message.message_id,
        reply_markup=call.message.reply_markup,
        parse_mode='HTML'
    )

    try:
        droplet.load()
        droplet.power_on()
    except Exception as e:
        bot.edit_message_text(
            text=f'⚠️ Kesalahan saat menyalakan droplet: <code>{str(e)}</code>',
            chat_id=call.from_user.id,
            message_id=call.message.message_id,
            parse_mode='HTML'
        )


def rebuild(call: CallbackQuery, droplet: digitalocean.Droplet, doc_id: str, droplet_id: str):
    bot.edit_message_text(
        text=f'{call.message.html_text}\n\n'
             '<b>🔄 Membangun ulang droplet, silakan segarkan nanti</b>',
        chat_id=call.from_user.id,
        message_id=call.message.message_id,
        reply_markup=call.message.reply_markup,
        parse_mode='HTML'
    )

    try:
        droplet.load()
        droplet.rebuild()
    except Exception as e:
        bot.edit_message_text(
            text=f'⚠️ Kesalahan saat membangun ulang droplet: <code>{str(e)}</code>',
            chat_id=call.from_user.id,
            message_id=call.message.message_id,
            parse_mode='HTML'
        )
        return

    bot.edit_message_text(
        text=f'{call.message.html_text}\n\n'
             f'<b>✅ Droplet sedang dibangun ulang</b>\n'
             f'Status akhir bisa dicek lewat tombol Refresh.',
        chat_id=call.from_user.id,
        message_id=call.message.message_id,
        parse_mode='HTML'
    )


def reset_password(call: CallbackQuery, droplet: digitalocean.Droplet, doc_id: str, droplet_id: str):
    bot.edit_message_text(
        text=f'{call.message.html_text}\n\n'
             '<b>🔄 Mereset password droplet, silakan segarkan nanti</b>',
        chat_id=call.from_user.id,
        message_id=call.message.message_id,
        reply_markup=call.message.reply_markup,
        parse_mode='HTML'
    )

    try:
        droplet.load()
        droplet.reset_root_password()
    except Exception as e:
        bot.edit_message_text(
            text=f'⚠️ Kesalahan saat mereset password droplet: <code>{str(e)}</code>',
            chat_id=call.from_user.id,
            message_id=call.message.message_id,
            parse_mode='HTML'
        )
        return

    bot.edit_message_text(
        text=f'{call.message.html_text}\n\n'
             f'<b>✅ Password droplet telah direset</b>\n'
             f'🔑 Password baru dikirim ke email akun DigitalOcean',
        chat_id=call.from_user.id,
        message_id=call.message.message_id,
        parse_mode='HTML'
    )