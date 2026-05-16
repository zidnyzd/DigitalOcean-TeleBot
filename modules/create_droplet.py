from typing import Union
from time import sleep

from telebot.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

import digitalocean

from _bot import bot
from utils.db import AccountsDB
from utils.localizer import localize_region
from utils.set_root_password_script import set_root_password_script
from utils.password_generator import password_generator

user_dict = {}

t = '<b>🚀 Buat Instance</b>\n\n'


def create_droplet(d: Union[Message, CallbackQuery], data: dict = None):
    data = data or {}
    next_func = data.get('nf', ['select_account'])[0]
    if next_func in globals():
        data.pop('nf', None)
        args = [d]
        if len(data.keys()) > 0:
            args.append(data)

        globals()[next_func](*args)


def select_account(d: Union[Message, CallbackQuery]):
    accounts = AccountsDB().all()
    markup = InlineKeyboardMarkup()
    for account in accounts:
        markup.add(
            InlineKeyboardButton(
                text=account['email'],
                callback_data=f'create_droplet?nf=select_region&doc_id={account.doc_id}'
            )
        )

    bot.send_message(
        text=f'{t}'
             '👤 Pilih Akun',
        chat_id=d.from_user.id,
        parse_mode='HTML',
        reply_markup=markup
    )


def select_region(call: CallbackQuery, data: dict):
    doc_id = data['doc_id'][0]

    account = AccountsDB().get(doc_id=doc_id)
    user_dict[call.from_user.id] = {
        'account': account
    }

    _t = t + f'👤 Akun: <code>{account["email"]}</code>\n\n'

    bot.edit_message_text(
        text=f'{_t}'
             f'🌍 Mengambil daftar Wilayah...',
        chat_id=call.from_user.id,
        message_id=call.message.message_id,
        parse_mode='HTML'
    )

    try:
        regions = digitalocean.Manager(token=account['token']).get_all_regions()
    except Exception as e:
        bot.edit_message_text(
            text=f'{_t}'
                 '⚠️ Kesalahan saat mengambil Wilayah: '
                 f'<code>{str(e)}</code>',
            chat_id=call.from_user.id,
            message_id=call.message.message_id,
            parse_mode='HTML'
        )
        return

    markup = InlineKeyboardMarkup(row_width=2)
    buttons = []
    for region in regions:
        if region.available:
            buttons.append(
                InlineKeyboardButton(
                    text=localize_region(slug=region.slug),
                    callback_data=f'create_droplet?nf=select_size&region={region.slug}'
                )
            )
    markup.add(*buttons)

    bot.edit_message_text(
        text=f'{_t}'
             f'🌍 Pilih Wilayah',
        chat_id=call.from_user.id,
        message_id=call.message.message_id,
        reply_markup=markup,
        parse_mode='HTML'
    )


def select_size(call: CallbackQuery, data: dict):
    region_slug = data['region'][0]

    user_dict[call.from_user.id].update({
        'region_slug': region_slug
    })

    _t = t + f'👤 Akun: <code>{user_dict[call.from_user.id]["account"]["email"]}</code>\n' \
             f'🌍 Wilayah: <code>{region_slug}</code>\n\n'

    bot.edit_message_text(
        text=f'{_t}'
             f'📏 Mengambil daftar Ukuran...',
        chat_id=call.from_user.id,
        message_id=call.message.message_id,
        parse_mode='HTML'
    )

    try:
        sizes = digitalocean.Manager(token=user_dict[call.from_user.id]['account']['token']).get_all_sizes()
    except Exception as e:
        bot.edit_message_text(
            text=f'{_t}'
                 '⚠️ Kesalahan saat mengambil Ukuran: '
                 f'<code>{str(e)}</code>',
            chat_id=call.from_user.id,
            message_id=call.message.message_id,
            parse_mode='HTML'
        )
        return

    markup = InlineKeyboardMarkup(row_width=2)
    buttons = []
    for size in sizes:
        if region_slug in size.regions:
            buttons.append(
                InlineKeyboardButton(
                    text=size.slug,
                    callback_data=f'create_droplet?nf=select_os&size={size.slug}'
                )
            )
    markup.add(*buttons)
    markup.row(
        InlineKeyboardButton(
            text='⬅️ Sebelumnya',
            callback_data=f'create_droplet?nf=select_region&doc_id={user_dict[call.from_user.id]["account"].doc_id}'
        )
    )

    bot.edit_message_text(
        text=f'{_t}'
             f'📏 Pilih Ukuran',
        chat_id=call.from_user.id,
        message_id=call.message.message_id,
        reply_markup=markup,
        parse_mode='HTML'
    )


def select_os(d: Union[Message, CallbackQuery], data: dict):
    size_slug = data['size'][0]

    user_dict[d.from_user.id].update({
        'size_slug': size_slug
    })

    _t = t + f'👤 Akun: <code>{user_dict[d.from_user.id]["account"]["email"]}</code>\n' \
             f'🌍 Wilayah: <code>{user_dict[d.from_user.id]["region_slug"]}</code>\n' \
             f'📏 Ukuran: <code>{size_slug}</code>\n\n'

    def get_os_markup():
        try:
            images = digitalocean.Manager(token=user_dict[d.from_user.id]['account']['token']).get_distro_images()
        except Exception as e:
            bot.edit_message_text(
                text=f'{_t}'
                     '⚠️ Kesalahan saat mengambil OS: '
                     f'<code>{str(e)}</code>',
                chat_id=d.from_user.id,
                message_id=d.message.message_id,
                parse_mode='HTML'
            )
            return InlineKeyboardMarkup()

        markup = InlineKeyboardMarkup(row_width=2)
        buttons = []
        for image in images:
            if image.distribution in ['Ubuntu', 'CentOS', 'Debian'] \
                    and image.public \
                    and image.status == 'available' \
                    and user_dict[d.from_user.id]["region_slug"] in image.regions:
                buttons.append(
                    InlineKeyboardButton(
                        text=f'{image.distribution} {image.name}',
                        callback_data=f'create_droplet?nf=get_name&image={image.slug}'
                    )
                )
        markup.add(*buttons)
        markup.row(
            InlineKeyboardButton(
                text='⬅️ Sebelumnya',
                callback_data=f'create_droplet?nf=select_size&region={user_dict[d.from_user.id]["region_slug"]}'
            )
        )

        return markup

    if type(d) == Message:
        msg = bot.send_message(
            text=f'{_t}'
                 f'🖼️ Mengambil daftar OS...',
            chat_id=d.from_user.id,
            parse_mode='HTML'
        )
        bot.edit_message_text(
            text=f'{_t}'
                 f'🖼️ Pilih OS',
            chat_id=d.from_user.id,
            message_id=msg.message_id,
            reply_markup=get_os_markup(),
            parse_mode='HTML'
        )

    elif type(d) == CallbackQuery:
        bot.edit_message_text(
            text=f'{_t}'
                 f'🖼️ Mengambil daftar OS...',
            chat_id=d.from_user.id,
            message_id=d.message.message_id,
            parse_mode='HTML'
        )
        bot.edit_message_text(
            text=f'{_t}'
                 f'🖼️ Pilih OS',
            chat_id=d.from_user.id,
            message_id=d.message.message_id,
            reply_markup=get_os_markup(),
            parse_mode='HTML'
        )


def get_name(call: CallbackQuery, data: dict):
    image_slug = data['image'][0]

    user_dict[call.from_user.id].update({
        'image_slug': image_slug
    })

    _t = t + f'👤 Akun: <code>{user_dict[call.from_user.id]["account"]["email"]}</code>\n' \
             f'🌍 Wilayah: <code>{user_dict[call.from_user.id]["region_slug"]}</code>\n' \
             f'📏 Ukuran: <code>{user_dict[call.from_user.id]["size_slug"]}</code>\n' \
             f'🖼️ OS: <code>{image_slug}</code>\n\n'

    msg = bot.edit_message_text(
        text=f'{_t}'
             '📝 Harap balas dengan Nama Instance, contoh: FighterTunnel\n\n'
             '/back ⬅️ Sebelumnya',
        chat_id=call.from_user.id,
        message_id=call.message.message_id,
        parse_mode='HTML'
    )
    bot.register_next_step_handler(msg, ask_create)


def ask_create(m: Message):
    if m.text == '/back':
        select_os(m, data={'size': [user_dict[m.from_user.id]["size_slug"]]})
        return

    _t = t + f'👤 Akun: <code>{user_dict[m.from_user.id]["account"]["email"]}</code>\n' \
             f'🌍 Wilayah: <code>{user_dict[m.from_user.id]["region_slug"]}</code>\n' \
             f'📏 Ukuran: <code>{user_dict[m.from_user.id]["size_slug"]}</code>\n' \
             f'🖼️ OS: <code>{user_dict[m.from_user.id]["image_slug"]}</code>\n' \
             f'📝 Nama: <code>{m.text}</code>\n\n'
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton(
            text='⬅️ Sebelumnya',
            callback_data=f'create_droplet?nf=get_name&image={user_dict[m.from_user.id]["image_slug"]}'
        ),
        InlineKeyboardButton(
            text='❌ Membatalkan',
            callback_data='create_droplet?nf=cancel_create'
        ),
    )
    markup.row(
        InlineKeyboardButton(
            text='✅ Buat',
            callback_data=f'create_droplet?nf=confirm_create&name={m.text}'
        )
    )

    bot.send_message(
        text=_t,
        chat_id=m.from_user.id,
        reply_markup=markup,
        parse_mode='HTML'
    )


def cancel_create(call: CallbackQuery):
    user_dict.pop(call.from_user.id, None)
    bot.edit_message_text(
        text=f'{call.message.html_text}\n\n'
             '<b>❌ Membatalkan</b>',
        chat_id=call.from_user.id,
        message_id=call.message.message_id,
        parse_mode='HTML'
    )


def confirm_create(call: CallbackQuery, data: dict):
    droplet_name = data['name'][0]
    password = password_generator()

    state = user_dict.get(call.from_user.id)
    if state is None:
        bot.edit_message_text(
            text=f'{call.message.html_text}\n\n'
                 '⚠️ Sesi pembuatan tidak ditemukan. Silakan mulai ulang dengan /add_vps.',
            chat_id=call.from_user.id,
            message_id=call.message.message_id,
            parse_mode='HTML'
        )
        return

    bot.edit_message_text(
        text=f'{call.message.html_text}\n\n'
             '<b>🔄 Membuat Instance...</b>',
        chat_id=call.from_user.id,
        message_id=call.message.message_id,
        parse_mode='HTML'
    )

    droplet = digitalocean.Droplet(
        token=state['account']['token'],
        name=droplet_name,
        region=state['region_slug'],
        image=state['image_slug'],
        size_slug=state['size_slug'],
        user_data=set_root_password_script(password)
    )

    try:
        droplet.create()
    except Exception as e:
        user_dict.pop(call.from_user.id, None)
        bot.edit_message_text(
            text=f'{call.message.html_text}\n\n'
                 '⚠️ Kesalahan saat membuat Instance: '
                 f'<code>{str(e)}</code>',
            chat_id=call.from_user.id,
            message_id=call.message.message_id,
            parse_mode='HTML'
        )
        return

    # Droplet sudah terlanjur dibuat. Mulai dari sini, error apapun tetap
    # harus mengembalikan referensi ke droplet agar user bisa kelola/hapus.
    doc_id = state['account'].doc_id
    detail_markup = InlineKeyboardMarkup()
    detail_markup.row(
        InlineKeyboardButton(
            text='🔍 Periksa Detailnya',
            callback_data=f'droplet_detail?doc_id={doc_id}&droplet_id={droplet.id}'
        )
    )

    try:
        for action in droplet.get_actions():
            while action.status != 'completed':
                sleep(3)
                action.load()
        droplet.load()

        while not droplet.ip_address:
            sleep(3)
            droplet.load()
    except Exception as e:
        user_dict.pop(call.from_user.id, None)
        bot.edit_message_text(
            text=f'{call.message.html_text}\n'
                 f'🆔 Droplet ID: <code>{droplet.id}</code>\n'
                 f'🔑 Kata Sandi: <code>{password}</code>\n\n'
                 '⚠️ Droplet sudah dibuat namun gagal mengambil status akhir: '
                 f'<code>{str(e)}</code>',
            chat_id=call.from_user.id,
            message_id=call.message.message_id,
            reply_markup=detail_markup,
            parse_mode='HTML'
        )
        return

    user_dict.pop(call.from_user.id, None)
    bot.edit_message_text(
        text=f'{call.message.html_text}\n'
             f'🌐 IP: <code>{droplet.ip_address}</code>\n'
             f'🔑 Kata Sandi: <code>{password}</code>\n\n'
             '<b>✅ Pembuatan Server Selesai</b>',
        chat_id=call.from_user.id,
        reply_markup=detail_markup,
        message_id=call.message.message_id,
        parse_mode='HTML'
    )
