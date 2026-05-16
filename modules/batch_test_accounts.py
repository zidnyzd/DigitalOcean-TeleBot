import json
from typing import Union

from telebot.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

import digitalocean
from digitalocean import DataReadError

from _bot import bot
from utils.db import AccountsDB
from utils.account_status import count_droplets, credit_label


def batch_test_accounts(d: Union[Message, CallbackQuery]):
    t = '<b>🔍 Akun Tes Batch</b>\n\n'
    markup = InlineKeyboardMarkup()

    msg = bot.send_message(
        text=f'{t}'
             f'🔄 Sedang Menguji...',
        chat_id=d.from_user.id,
        parse_mode='HTML',
    )

    accounts = AccountsDB().all()
    checked_accounts = []
    failed_accounts = []

    for account in accounts:
        try:
            account_balance = digitalocean.Balance().get_object(api_token=account['token'])
            account_balance.email = account['email']
            account_balance.droplet_count = count_droplets(account['token'])

            checked_accounts.append(account_balance)

        except DataReadError:
            failed_accounts.append(account['email'])
        except Exception as e:
            bot.edit_message_text(
                text=f'{t}'
                     f'⚠️ Kesalahan saat memeriksa akun: <code>{str(e)}</code>',
                chat_id=d.from_user.id,
                message_id=msg.message_id,
                parse_mode='HTML'
            )
            return

    t += f'<b>Total {len(accounts)} Akun</b>\n\n'

    if checked_accounts:
        t += f'✅ Tes Berhasil {len(checked_accounts)} akun:\n'
        for ab in checked_accounts:
            status = credit_label(
                ab.account_balance,
                ab.month_to_date_usage,
                ab.droplet_count,
            )
            t += (
                f'<code>{ab.email}</code> | '
                f'Saldo: <code>{ab.account_balance}</code> | '
                f'Sekarang: <code>{ab.month_to_date_balance}</code> | '
                f'{status}\n'
            )
        t += '\n'

    if failed_accounts:
        t += f'❌ Tes Gagal {len(failed_accounts)} akun:\n'
        for email in failed_accounts:
            t += f'<code>{email}</code>\n'
        markup.add(
            InlineKeyboardButton(
                text='🗑️ Hapus Akun Gagal',
                callback_data=json.dumps({
                    't': 'batch_test_delete_accounts'
                })
            )
        )

    bot.edit_message_text(
        text=t,
        chat_id=d.from_user.id,
        message_id=msg.message_id,
        parse_mode='HTML',
        reply_markup=markup
    )
