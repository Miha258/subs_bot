from aiogram import types, Dispatcher
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher import FSMContext
from create_bot import *
from admin.utils import *
from aiogram.dispatcher.filters.state import State, StatesGroup


class GlobalSettingsStates(StatesGroup):
    NOTION_TOKEN = State()
    CHAT = State()
    SUPPORT = State()

settings_msg = None
async def send_settings_menu(message: types.Message, _return = False):
    keyboard = InlineKeyboardMarkup(row_width=1)
    config = load_config()
    buttons = [
        # InlineKeyboardButton("Установить токен API для Notion", callback_data="set_notion_token"),
        InlineKeyboardButton("Установить чат", callback_data="set_chat_id"),
        InlineKeyboardButton("Установить контакт поддержки", callback_data="set_support"),
    ]
    chat_id = config.get('chat')
    if chat_id:
        chat = await bot.get_chat(chat_id)
    keyboard.add(*buttons)
    text = f"""
Выберите параметр, который вы хотите настроить:
                        
Notion API токен: <pre>{config.get("notion_api_token")}</pre>
Цена тарифа: <strong>{config.get("tariff_price")}</strong>
Телеграм чат: <strong>{chat.username if chat_id else ""}</strong>
Контакт поддержки: <strong>{config.get("support")}</strong>
    """
    if not _return:
        await message.answer(text, reply_markup = keyboard, parse_mode = "html")
    else:
        return text



async def settins_menu(message: types.Message):
    await send_settings_menu(message)


async def process_callback(callback_query: types.CallbackQuery, state: FSMContext):
    global settings_msg
    data = callback_query.data
    chat_id = callback_query.message.chat.id
    
    if data == "set_notion_token":
        await state.set_state(GlobalSettingsStates.NOTION_TOKEN)
        await bot.send_message(chat_id, "Введіть своє значення FDV:")
    elif data == "set_chat_id":
        await state.set_state(GlobalSettingsStates.CHAT)
        await bot.send_message(chat_id, "Введіть айди чата:")
    elif data == "set_support":
        await state.set_state(GlobalSettingsStates.SUPPORT)

    settings_msg = callback_query.message.message_id


async def set_notion_token(message: types.Message, state: FSMContext):
    change_param('notion_token', message.text)
    text = await send_settings_menu(message, True)
    await message.edit_text(text, parse_mode = "html")
    await state.finish()


async def set_chat_id(message: types.Message, state: FSMContext):
    try:
        await bot.get_chat(message.text)
    except Exception:
        return await message.answer('Не могу найти чат, попробуйте другой')
    change_param('set_chat_id', message.text)
    text = await send_settings_menu(message, True)
    await message.edit_text(text, parse_mode = "html")
    await state.finish()

async def set_support(message: types.Message, state: FSMContext):
    change_param('support', message.text)
    text = await send_settings_menu(message, True)
    await message.edit_text(text, parse_mode = "html")
    await state.finish()


def register_settins(dp: Dispatcher):
    dp.register_message_handler(settins_menu, lambda message: message.text == 'Настройки', state = "*")
    dp.register_callback_query_handler(process_callback, lambda callback_query: callback_query.data in ["set_notion_token", "set_chat_id", "set_support"])
    dp.register_message_handler(set_chat_id, state = GlobalSettingsStates.CHAT)
    dp.register_message_handler(set_notion_token, state = GlobalSettingsStates.NOTION_TOKEN)
    dp.register_message_handler(set_support, state = GlobalSettingsStates.SUPPORT)
