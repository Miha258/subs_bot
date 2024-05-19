import random
import string
from db import session, Promocode
from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup


class SubscriptionPromo(StatesGroup):
    TYPE = State()
    DAYS = State()
    ACTIVATIONS = State()
    PERCENT = State()

class EditPromoState(StatesGroup):
    EDITING = State()
    DAYS = State()
    ACTIVATIONS = State()
    PERCENT = State()


def generate_promocode():
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return code

async def view_promocodes(message: types.Message, state: FSMContext, _return = False):
    await state.finish()
    promocodes = session.query(Promocode).all()
    keyboard = types.InlineKeyboardMarkup()

    if promocodes:
        for promo in promocodes:
            button_text = f"{promo.code}: {str(promo.days) + ' дней ' if promo.days else 'на ' + str(promo.discount) + ' процентов'}, {promo.activations_left} активаций"
            callback_data = f"edit_promo:{promo.id}"
            keyboard.add(types.InlineKeyboardButton(button_text, callback_data = callback_data))
        keyboard.add(types.InlineKeyboardButton("Добавить промокод", callback_data = "add_promo"))
        if _return:
            return "Выберите промокод для редактирования:", keyboard
        await message.answer("Выберите промокод для редактирования:", reply_markup=keyboard)
    else:
        keyboard.add(types.InlineKeyboardButton("Добавить промокод", callback_data = "add_promo"))
        if _return:
            return "Выберите промокод для редактирования:", keyboard
        await message.answer("Нет доступных промокодов. Создйте первый:", reply_markup = keyboard)


def get_edit_promo_kb(promo: Promocode):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(f"Редактировать активации ({promo.activations_left})", callback_data = f"edit_promo_activations:{promo.id}"))
    
    promo_type: str = promo.type
    match promo_type:
        case "Подписка":
            keyboard.add(types.InlineKeyboardButton(f"Редактировать дни ({promo.days})", callback_data = f"edit_promo_days:{promo.id}"))
        case "Скидка":
            keyboard.add(types.InlineKeyboardButton(f"Редактировать процент ({promo.discount})", callback_data = f"edit_promo_percent:{promo.id}"))
    
    keyboard.add(types.InlineKeyboardButton("Удалить промокод", callback_data = f"delete_promo:{promo.id}"))
    keyboard.add(types.InlineKeyboardButton("Назад", callback_data = f"back_to_promo_list"))
    return keyboard


async def edit_promocode(query: types.CallbackQuery, state: FSMContext):
    promo_id = int(query.data.split(':')[1])
    promo = session.query(Promocode).filter_by(id = promo_id).first()
    msg = await query.message.answer(f'Редактирование промокода: <strong>{promo.code}</strong>\nТип: <strong>{promo.type}</strong>', parse_mode = "html", reply_markup = get_edit_promo_kb(promo))
    await state.set_data({"target_msg": msg})
    await state.set_state(EditPromoState.EDITING)


async def edit_promocode_handler(query: types.CallbackQuery, state: FSMContext):
    edit_action = query.data.split(':')[0]
    promo_id = int(query.data.split(':')[1])
    await state.update_data({"promo_id": promo_id})
    
    match edit_action:
        case "delete_promo":
            await delete_promocode(query, state)
        case "edit_promo_activations":
            await query.message.answer('Введите количество активаций:')
            await state.set_state(EditPromoState.ACTIVATIONS)
        case "edit_promo_days":
            await query.message.answer("Введите количество дней для подписки:")
            await state.set_state(EditPromoState.DAYS)
        case "edit_promo_percent":
            await query.message.answer('Введите процент <strong>(от 1 до 100):</strong>', parse_mode = "html")
            await state.set_state(EditPromoState.PERCENT)


async def delete_promocode(query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    promo_id = data["promo_id"]
    promo = session.query(Promocode).filter_by(id = promo_id).first()
    session.delete(promo)
    session.commit()
    await view_promocodes(query.message, state)


async def edit_promo_activations(message: types.Message, state: FSMContext):
    data = await state.get_data()
    promo_id = data["promo_id"]
    promo = session.query(Promocode).filter_by(id = promo_id).first()
    target_msg = data["target_msg"]
    try:
        activations = int(message.text)
        promo.activations_left = activations
        session.commit()
        await state.finish()
        await message.delete()
        await target_msg.edit_reply_markup(get_edit_promo_kb(promo))
    except ValueError:
        await message.answer("Пожалуйста, введите число:")


async def edit_promo_days(message: types.Message, state: FSMContext):
    data = await state.get_data()
    promo_id = data["promo_id"]
    promo = session.query(Promocode).filter_by(id = promo_id).first()
    target_msg = data["target_msg"]
    try:
        days = int(message.text)
        promo.days = days
        session.commit()
        await state.finish()
        await message.delete()
        await target_msg.edit_reply_markup(get_edit_promo_kb(promo))
    except ValueError:
        await message.answer("Пожалуйста, введите число:")


async def edit_promo_percent(message: types.Message, state: FSMContext):
    data = await state.get_data()
    promo_id = data["promo_id"]
    promo = session.query(Promocode).filter_by(id = promo_id).first()
    target_msg = data["target_msg"]
    try:
        percent = int(message.text)
        if percent > 1 and percent < 101:
            promo.discount = percent
            session.commit()
            await state.finish()
            await message.delete()
            await target_msg.edit_reply_markup(get_edit_promo_kb(promo))
        else:
            await message.answer('Введите процент <strong>(от 1 до 100):</strong>', parse_mode = "html")
    except ValueError:
        await message.answer("Пожалуйста, введите число:")

    session.commit()
    await message.edit_reply_markup(get_edit_promo_kb(promo))


async def create_subscription_promocode(query: types.CallbackQuery, state: FSMContext):
    await query.message.answer("Виберите тип промокода", reply_markup = types.ReplyKeyboardMarkup(keyboard = [[
        types.KeyboardButton('Скидка'),
        types.KeyboardButton('Подписка')
    ]]))
    await state.set_state(SubscriptionPromo.TYPE)



async def process_subscription_type(message: types.Message, state: FSMContext):
    promo_type = message.text
    await state.set_data({"type": promo_type})

    match promo_type:
        case "Скидка":
            await message.answer('Введите процент <strong>(от 1 до 100):</strong>', parse_mode = "html")
            await state.set_state(SubscriptionPromo.PERCENT)
        case "Подписка":
            await message.answer('Введите количество дней:')
            await state.set_state(SubscriptionPromo.DAYS)



async def process_promo_percent(message: types.Message, state: FSMContext):
    try:
        percent = int(message.text)
        if percent > 0 and percent < 101:
            await message.answer('Введите количество активаций:')
            await state.update_data({"percent": percent})
            await state.set_state(SubscriptionPromo.ACTIVATIONS)
        else:
            await message.answer('Введите процент <strong>(от 1 до 100):</strong>', parse_mode = "html")
    except ValueError:
        await message.answer("Пожалуйста, введите число:")


async def process_promo_days(message: types.Message, state: FSMContext):
    try:
        days = int(message.text)
        await message.answer('Введите количество активаций:')
        await state.update_data({"days": days})
        await state.set_state(SubscriptionPromo.ACTIVATIONS)
    except ValueError:
        await message.answer("Пожалуйста, введите число:")

async def process_activations(message: types.Message, state: FSMContext):
    try:
        async with state.proxy() as data:
            activations = int(message.text)
            code = generate_promocode()
            promo = Promocode(code = code, discount = data.get("percent"), days = data.get('days'), activations_left = activations, type = data["type"])
            session.add(promo)
            session.commit()
            await message.answer(f'Промокод <strong>{code}</strong> успешно создан!', parse_mode = "html")
            await view_promocodes(message, state)
            await state.finish()
    except ValueError:
        await message.answer("Пожалуйста, введите число:")


async def back_to_promo_list(query: types.CallbackQuery, state: FSMContext):
    text, kb = await view_promocodes(query.message, state, True)
    await query.message.edit_text(text, reply_markup = kb)

def register_promo(dp: Dispatcher):
    dp.register_message_handler(view_promocodes, text = 'Управлять промокодами', state = "*")
    dp.register_callback_query_handler(back_to_promo_list, lambda cb: cb.data == 'back_to_promo_list', state = "*")
    dp.register_callback_query_handler(create_subscription_promocode, lambda cb: cb.data == 'add_promo')
    dp.register_callback_query_handler(edit_promocode, lambda cb: "edit_promo" in cb.data)
    dp.register_callback_query_handler(edit_promocode_handler, state = EditPromoState.EDITING)

    dp.register_message_handler(edit_promo_activations, state = EditPromoState.ACTIVATIONS)
    dp.register_message_handler(edit_promo_days, state = EditPromoState.DAYS)
    dp.register_message_handler(edit_promo_percent, state = EditPromoState.PERCENT)
    
    dp.register_message_handler(process_subscription_type, lambda m: m.text in ("Скидка", "Подписка"), state = SubscriptionPromo.TYPE)
    dp.register_message_handler(process_promo_percent, state = SubscriptionPromo.PERCENT)
    dp.register_message_handler(process_promo_days, state = SubscriptionPromo.DAYS)
    dp.register_message_handler(process_activations, state = SubscriptionPromo.ACTIVATIONS)


