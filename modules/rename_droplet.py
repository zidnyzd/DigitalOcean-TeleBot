from telebot.types import (
    CallbackQuery,
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

import digitalocean
import requests
import json

from _bot import bot
from utils.db import AccountsDB

# Dictionary to store user states for rename operations
rename_states = {}

def rename_droplet(call: CallbackQuery, data: dict):
    """Handle rename droplet callback"""
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
    
    # Store the rename state
    rename_states[call.from_user.id] = {
        'doc_id': doc_id,
        'droplet_id': droplet_id,
        'action': 'rename',
        'current_name': droplet.name
    }
    
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton(
            text='🔙 Batal',
            callback_data=f'droplet_detail?doc_id={doc_id}&droplet_id={droplet_id}'
        )
    )
    
    bot.edit_message_text(
        text=f'<b>✏️ Rename Droplet</b>\n\n'
             f'🏷️ Nama saat ini: <code>{droplet.name}</code>\n\n'
             '📝 Silakan kirim nama baru untuk droplet ini.\n'
             'Nama harus 3-63 karakter dan hanya boleh mengandung huruf, angka, dan tanda hubung.',
        chat_id=call.from_user.id,
        message_id=call.message.message_id,
        parse_mode='HTML',
        reply_markup=markup
    )

def handle_rename_input(message: Message):
    """Handle the new name input from user"""
    user_id = message.from_user.id
    
    if user_id not in rename_states or rename_states[user_id]['action'] != 'rename':
        return False
    
    new_name = message.text.strip()
    
    # Validate name
    if len(new_name) < 3 or len(new_name) > 63:
        bot.reply_to(
            message,
            '❌ Nama harus antara 3-63 karakter. Silakan coba lagi.'
        )
        return True
    
    # Check for valid characters (letters, numbers, hyphens only)
    if not new_name.replace('-', '').replace('_', '').isalnum():
        bot.reply_to(
            message,
            '❌ Nama hanya boleh mengandung huruf, angka, dan tanda hubung. Silakan coba lagi.'
        )
        return True
    
    # Get stored data
    doc_id = rename_states[user_id]['doc_id']
    droplet_id = rename_states[user_id]['droplet_id']
    current_name = rename_states[user_id]['current_name']
    
    try:
        account = AccountsDB().get(doc_id=doc_id)
    except Exception as e:
        bot.reply_to(
            message,
            f'⚠️ Kesalahan saat mengambil akun: <code>{str(e)}</code>',
            parse_mode='HTML'
        )
        del rename_states[user_id]
        return True
    
    # Show processing message
    processing_msg = bot.reply_to(
        message,
        '🔄 Sedang mengubah nama droplet...'
    )
    
    try:
        # Use DigitalOcean API to rename the droplet using droplet-action endpoint
        headers = {
            'Authorization': f'Bearer {account["token"]}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'type': 'rename',
            'name': new_name
        }
        
        response = requests.post(
            f'https://api.digitalocean.com/v2/droplets/{droplet_id}/actions',
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 201:
            # Success message
            bot.edit_message_text(
                text=f'✅ <b>Nama droplet berhasil diubah!</b>\n\n'
                     f'🏷️ Nama lama: <code>{current_name}</code>\n'
                     f'🏷️ Nama baru: <code>{new_name}</code>',
                chat_id=message.chat.id,
                message_id=processing_msg.message_id,
                parse_mode='HTML'
            )
        else:
            # Handle error response more safely
            try:
                error_data = response.json()
                error_message = error_data.get('message', f'HTTP {response.status_code}')
            except:
                error_message = f'HTTP {response.status_code}: {response.text[:100]}'
            
            bot.edit_message_text(
                text=f'❌ <b>Gagal mengubah nama droplet</b>\n\n'
                     f'Error: <code>{error_message}</code>',
                chat_id=message.chat.id,
                message_id=processing_msg.message_id,
                parse_mode='HTML'
            )
        
        # Clear the state
        del rename_states[user_id]
        
    except Exception as e:
        bot.edit_message_text(
            text=f'❌ <b>Gagal mengubah nama droplet</b>\n\n'
                 f'Error: <code>{str(e)}</code>',
            chat_id=message.chat.id,
            message_id=processing_msg.message_id,
            parse_mode='HTML'
        )
        del rename_states[user_id]
    
    return True

def cancel_rename(call: CallbackQuery, data: dict):
    """Cancel rename operation"""
    user_id = call.from_user.id
    
    if user_id in rename_states:
        del rename_states[user_id]
    
    # Go back to droplet detail
    doc_id = data['doc_id'][0]
    droplet_id = data['droplet_id'][0]
    
    # Import and call droplet_detail function
    from modules.droplet_detail import droplet_detail
    droplet_detail(call, data)
