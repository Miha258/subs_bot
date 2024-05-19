from aiogram import types


def get_menu_kb():
    kb = types.InlineKeyboardMarkup(inline_keyboard = [
        [types.InlineKeyboardButton(f"Сгенрировать ссылкау", callback_data = "generate_invite_link")]
    ])
    return kb

def back_to_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard = True)
    keyboard.add(types.KeyboardButton("Назад"))
    return keyboard

def launch_adds(with_delay = False):
    keyboard = types.InlineKeyboardMarkup(resize_keyboard = True)
    keyboard.add(types.InlineKeyboardButton("Назад", callback_data = "back_to_main_admin_menu")),
    
    if not with_delay:
        keyboard.add(types.InlineKeyboardButton("Отправить", callback_data = "launch_adds_sending"))
    else:
        keyboard.add(types.InlineKeyboardButton("Запланировать", callback_data = "launch_adds_sending_with_delay"))
    return keyboard

def get_main_admin_menu_kb():
    keyboard_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = [
        types.KeyboardButton(text="Статистика"),
        types.KeyboardButton(text="Продлить подписку"),
        types.KeyboardButton(text="Настройки"),
        types.KeyboardButton(text="Управлять промокодами"),
        types.KeyboardButton(text="Способы оплаты"),
        types.KeyboardButton(text="Сделать рассылку"),
        types.KeyboardButton(text="Управлять тарифами")
    ]
    keyboard_markup.add(*buttons)
    return keyboard_markup

def get_user_panel_kb(is_subscribed = False):
    keyboard_markup = types.InlineKeyboardMarkup(inline_keyboard = [
        [types.InlineKeyboardButton(text = "Приобрести подписку", callback_data = "buy_subscription")] if not is_subscribed else [types.InlineKeyboardButton(text = "Продлить подпсику", callback_data = "buy_subscription")],
        [types.InlineKeyboardButton(text = "Использовать промокод", callback_data = "use_promocode")],
        [types.InlineKeyboardButton(text = 'Подключить свой емейл к Notion', callback_data = "add_notion_email")]
    ])
   
    if is_subscribed:
        keyboard_markup.add(types.InlineKeyboardButton(text = 'Получить инвайт в группу в тг', callback_data = "get_invite_on_tg"),)
        keyboard_markup.add(types.InlineKeyboardButton(text = 'Получить инвайт в Notion', callback_data = "get_invite_on_notion"),)
    keyboard_markup.add(types.InlineKeyboardButton(text = 'Вернуться', callback_data = 'back_to_user_menu'))
    return keyboard_markup