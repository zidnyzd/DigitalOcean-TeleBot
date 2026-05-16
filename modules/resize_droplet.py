from time import sleep, monotonic

from telebot.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

import digitalocean
import requests

from _bot import bot
from utils.db import AccountsDB
from utils.localizer import localize_region

# Per-user resize state, keyed by Telegram user id.
# Shape: {
#   'doc_id', 'droplet_id', 'token',
#   'current_name', 'current_size_slug', 'region_slug', 'original_status',
#   'target_size_slug', 'include_disk',
# }
user_dict = {}

_HEADER = '<b>📐 Resize Droplet</b>\n\n'

# Hard cap for waiting on shutdown / resize actions, in seconds.
_SHUTDOWN_TIMEOUT = 90
_RESIZE_TIMEOUT = 600
_POWER_ON_TIMEOUT = 120


def resize_droplet(call: CallbackQuery, data: dict):
    """Sub-router for the resize wizard. `nf` selects the next step."""
    next_func = data.get('nf', ['select_size'])[0]
    if next_func not in globals():
        return

    payload = {k: v for k, v in data.items() if k != 'nf'}
    globals()[next_func](call, payload)


def select_size(call: CallbackQuery, data: dict):
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
            text=f'⚠️ Kesalahan saat mengambil droplet: <code>{str(e)}</code>',
            chat_id=call.from_user.id,
            message_id=call.message.message_id,
            parse_mode='HTML'
        )
        return

    region_slug = droplet.region['slug']
    current_size = droplet.size_slug

    bot.edit_message_text(
        text=f'{_HEADER}'
             f'🏷️ Droplet: <code>{droplet.name}</code>\n'
             f'📏 Ukuran saat ini: <code>{current_size}</code>\n'
             f'🌍 Wilayah: <code>{localize_region(region_slug)}</code>\n\n'
             f'🔄 Mengambil daftar ukuran...',
        chat_id=call.from_user.id,
        message_id=call.message.message_id,
        parse_mode='HTML'
    )

    try:
        sizes = digitalocean.Manager(token=account['token']).get_all_sizes()
    except Exception as e:
        bot.edit_message_text(
            text=f'{_HEADER}'
                 f'⚠️ Kesalahan saat mengambil ukuran: <code>{str(e)}</code>',
            chat_id=call.from_user.id,
            message_id=call.message.message_id,
            parse_mode='HTML'
        )
        return

    user_dict[call.from_user.id] = {
        'doc_id': doc_id,
        'droplet_id': droplet_id,
        'token': account['token'],
        'current_name': droplet.name,
        'current_size_slug': current_size,
        'region_slug': region_slug,
        'original_status': droplet.status,
        'include_disk': False,
    }

    candidates = [
        s for s in sizes
        if s.available and region_slug in s.regions and s.slug != current_size
    ]
    candidates.sort(key=lambda s: s.price_monthly or 0)

    markup = InlineKeyboardMarkup(row_width=1)
    for size in candidates:
        price = f'${size.price_monthly:g}/mo' if size.price_monthly else '?'
        markup.add(
            InlineKeyboardButton(
                text=f'{size.slug} — {price}',
                callback_data=f'resize_droplet?nf=review&size={size.slug}'
            )
        )
    markup.row(
        InlineKeyboardButton(
            text='🔙 Batal',
            callback_data=f'cancel_resize?doc_id={doc_id}&droplet_id={droplet_id}'
        )
    )

    if not candidates:
        bot.edit_message_text(
            text=f'{_HEADER}'
                 f'🏷️ Droplet: <code>{droplet.name}</code>\n'
                 f'📏 Ukuran saat ini: <code>{current_size}</code>\n\n'
                 'ℹ️ Tidak ada ukuran lain yang tersedia di wilayah ini.',
            chat_id=call.from_user.id,
            message_id=call.message.message_id,
            reply_markup=markup,
            parse_mode='HTML'
        )
        return

    bot.edit_message_text(
        text=f'{_HEADER}'
             f'🏷️ Droplet: <code>{droplet.name}</code>\n'
             f'📏 Ukuran saat ini: <code>{current_size}</code>\n'
             f'🌍 Wilayah: <code>{localize_region(region_slug)}</code>\n\n'
             '📐 Pilih ukuran baru:',
        chat_id=call.from_user.id,
        message_id=call.message.message_id,
        reply_markup=markup,
        parse_mode='HTML'
    )


def review(call: CallbackQuery, data: dict):
    state = user_dict.get(call.from_user.id)
    if state is None:
        bot.edit_message_text(
            text='⚠️ Sesi resize tidak ditemukan. Silakan mulai ulang dari detail droplet.',
            chat_id=call.from_user.id,
            message_id=call.message.message_id
        )
        return

    if 'size' in data:
        state['target_size_slug'] = data['size'][0]

    _render_review(call, state)


def toggle_disk(call: CallbackQuery, data: dict):
    state = user_dict.get(call.from_user.id)
    if state is None:
        bot.edit_message_text(
            text='⚠️ Sesi resize tidak ditemukan. Silakan mulai ulang dari detail droplet.',
            chat_id=call.from_user.id,
            message_id=call.message.message_id
        )
        return

    state['include_disk'] = not state.get('include_disk', False)
    _render_review(call, state)


def _render_review(call: CallbackQuery, state: dict):
    include_disk = state.get('include_disk', False)
    disk_label = '✅ Termasuk disk (permanen)' if include_disk \
        else '⬜ CPU/RAM saja (bisa dikembalikan)'

    will_shutdown = state['original_status'] == 'active'
    shutdown_note = (
        '\n⚠️ Droplet sedang aktif. Akan dimatikan sementara, di-resize, '
        'lalu dinyalakan kembali secara otomatis.'
        if will_shutdown else ''
    )

    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton(
            text=disk_label,
            callback_data='resize_droplet?nf=toggle_disk'
        )
    )
    markup.row(
        InlineKeyboardButton(
            text='✅ Konfirmasi resize',
            callback_data='resize_droplet?nf=confirm'
        ),
    )
    markup.row(
        InlineKeyboardButton(
            text='🔙 Batal',
            callback_data=f'cancel_resize?doc_id={state["doc_id"]}&droplet_id={state["droplet_id"]}'
        )
    )

    bot.edit_message_text(
        text=f'{_HEADER}'
             f'🏷️ Droplet: <code>{state["current_name"]}</code>\n'
             f'📏 Ukuran lama: <code>{state["current_size_slug"]}</code>\n'
             f'📐 Ukuran baru: <code>{state["target_size_slug"]}</code>\n'
             f'💾 Mode disk: {"termasuk disk" if include_disk else "CPU/RAM saja"}\n'
             f'{shutdown_note}\n\n'
             'Resize dengan disk bersifat <b>permanen</b> dan tidak bisa diturunkan kembali. '
             'Tanpa disk hanya mengubah CPU/RAM dan dapat dikembalikan ke ukuran semula.',
        chat_id=call.from_user.id,
        message_id=call.message.message_id,
        parse_mode='HTML',
        reply_markup=markup
    )


def confirm(call: CallbackQuery, data: dict):
    state = user_dict.get(call.from_user.id)
    if state is None:
        bot.edit_message_text(
            text='⚠️ Sesi resize tidak ditemukan. Silakan mulai ulang dari detail droplet.',
            chat_id=call.from_user.id,
            message_id=call.message.message_id
        )
        return

    chat_id = call.from_user.id
    msg_id = call.message.message_id
    droplet_id = state['droplet_id']
    token = state['token']

    def _set_status(text: str, markup=None):
        bot.edit_message_text(
            text=text,
            chat_id=chat_id,
            message_id=msg_id,
            parse_mode='HTML',
            reply_markup=markup
        )

    try:
        # 1. Pastikan droplet mati.
        if state['original_status'] == 'active':
            _set_status(f'{_HEADER}🛑 Mematikan droplet...')
            if not _shutdown_and_wait(token, droplet_id):
                _set_status(
                    f'{_HEADER}⚠️ Droplet tidak mati setelah {_SHUTDOWN_TIMEOUT} detik. '
                    'Coba matikan manual dari menu detail lalu ulangi resize.'
                )
                user_dict.pop(call.from_user.id, None)
                return

        # 2. Trigger resize.
        _set_status(
            f'{_HEADER}📐 Mengubah ukuran ke '
            f'<code>{state["target_size_slug"]}</code>...'
        )
        action_id, err = _trigger_resize(
            token, droplet_id,
            state['target_size_slug'],
            state['include_disk']
        )
        if err is not None:
            _set_status(f'{_HEADER}⚠️ Gagal memulai resize: <code>{err}</code>')
            user_dict.pop(call.from_user.id, None)
            return

        # 3. Tunggu action selesai.
        ok, err = _wait_action(token, droplet_id, action_id, _RESIZE_TIMEOUT)
        if not ok:
            _set_status(
                f'{_HEADER}⚠️ Resize belum selesai: <code>{err}</code>\n'
                'Cek ulang status droplet sebentar lagi.'
            )
            user_dict.pop(call.from_user.id, None)
            return

        # 4. Nyalakan kembali kalau sebelumnya aktif.
        powered_back_on = True
        if state['original_status'] == 'active':
            _set_status(f'{_HEADER}⚡ Menyalakan kembali droplet...')
            powered_back_on = _power_on_and_wait(token, droplet_id)

    except Exception as e:
        _set_status(f'{_HEADER}⚠️ Kesalahan tak terduga: <code>{str(e)}</code>')
        user_dict.pop(call.from_user.id, None)
        return

    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton(
            text='🔍 Lihat detail droplet',
            callback_data=f'droplet_detail?doc_id={state["doc_id"]}&droplet_id={droplet_id}'
        )
    )

    final = (
        f'{_HEADER}'
        f'🏷️ Droplet: <code>{state["current_name"]}</code>\n'
        f'📏 Ukuran lama: <code>{state["current_size_slug"]}</code>\n'
        f'📐 Ukuran baru: <code>{state["target_size_slug"]}</code>\n'
        f'💾 Mode disk: {"termasuk disk" if state["include_disk"] else "CPU/RAM saja"}\n\n'
        '<b>✅ Resize selesai</b>'
    )
    if not powered_back_on:
        final += (
            '\n⚠️ Resize berhasil tetapi droplet belum kembali ke status aktif. '
            'Coba nyalakan manual dari menu detail.'
        )

    user_dict.pop(call.from_user.id, None)
    _set_status(final, markup=markup)


def cancel_resize(call: CallbackQuery, data: dict):
    user_dict.pop(call.from_user.id, None)
    from modules.droplet_detail import droplet_detail
    droplet_detail(call, data)


# ---------- API helpers ----------

def _trigger_resize(token: str, droplet_id: str, size_slug: str, include_disk: bool):
    """Returns (action_id, None) on success, (None, error_message) on failure."""
    try:
        response = requests.post(
            f'https://api.digitalocean.com/v2/droplets/{droplet_id}/actions',
            headers={
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
            },
            json={'type': 'resize', 'size': size_slug, 'disk': include_disk},
            timeout=30
        )
    except Exception as e:
        return None, str(e)

    if response.status_code != 201:
        try:
            msg = response.json().get('message', f'HTTP {response.status_code}')
        except ValueError:
            msg = f'HTTP {response.status_code}: {response.text[:120]}'
        return None, msg

    try:
        return response.json()['action']['id'], None
    except Exception as e:
        return None, f'respon API tidak valid: {e}'


def _wait_action(token: str, droplet_id: str, action_id: int, timeout: int):
    """Poll action status until completed or timeout."""
    deadline = monotonic() + timeout
    headers = {'Authorization': f'Bearer {token}'}
    url = f'https://api.digitalocean.com/v2/droplets/{droplet_id}/actions/{action_id}'

    while monotonic() < deadline:
        try:
            r = requests.get(url, headers=headers, timeout=30)
        except Exception as e:
            return False, str(e)

        if r.status_code != 200:
            try:
                msg = r.json().get('message', f'HTTP {r.status_code}')
            except ValueError:
                msg = f'HTTP {r.status_code}'
            return False, msg

        status = r.json().get('action', {}).get('status')
        if status == 'completed':
            return True, None
        if status == 'errored':
            return False, 'action errored'
        sleep(3)

    return False, f'timeout setelah {timeout} detik'


def _shutdown_and_wait(token: str, droplet_id: str) -> bool:
    droplet = digitalocean.Droplet(token=token, id=droplet_id)
    try:
        droplet.load()
        if droplet.status != 'off':
            droplet.shutdown()
    except Exception:
        return False

    deadline = monotonic() + _SHUTDOWN_TIMEOUT
    while monotonic() < deadline:
        try:
            droplet.load()
        except Exception:
            return False
        if droplet.status == 'off':
            return True
        sleep(3)
    return False


def _power_on_and_wait(token: str, droplet_id: str) -> bool:
    droplet = digitalocean.Droplet(token=token, id=droplet_id)
    try:
        droplet.load()
        if droplet.status != 'active':
            droplet.power_on()
    except Exception:
        return False

    deadline = monotonic() + _POWER_ON_TIMEOUT
    while monotonic() < deadline:
        try:
            droplet.load()
        except Exception:
            return False
        if droplet.status == 'active':
            return True
        sleep(3)
    return False
