from aiogram.dispatcher import FSMContext
from aiogram import Dispatcher, types
from admin.tariffs import get_tarrifs_list_kb
from datetime import datetime, timedelta
from create_bot import admins, bot
from db import session, User, Tariffs, PaymentMethod, Promocode, Transaction
from admin.utils import load_config
from keyboards import *
from aiogram.dispatcher.filters.state import State, StatesGroup
from dateutil.relativedelta import relativedelta

class UserStates(StatesGroup):
    PROMOCODE = State()
    ADD_EMAIL = State()
    CHOOSE_TARIF = State()
    CHOOSE_METHOD = State()
    SET_SCREENSHOT = State()
    SET_COMMENT = State()
    SET_COMMENT_ADMIN = State()

async def process_user_menu(query: types.CallbackQuery, state: FSMContext):
    data = query.data
    match data:
        case "buy_subscription":
            await buy_subscription(query, state)
        case "use_promocode":
            await query.message.answer("Введите ваш промокод:")
            await state.set_state(UserStates.PROMOCODE)
        case "add_notion_email":
            await query.message.answer("Введите ваш email для Notion:")
            await state.set_state(UserStates.ADD_EMAIL)
        case "get_invite_on_tg":
            user = session.query(User).filter_by(chat_id = query.from_user.id).first()
            if user.invite_link_retries != 0:
                user.invite_link_retries = user.invite_link_retries - 1
                session.commit()
                config = load_config()
                invite_url = await bot.create_chat_invite_link(config.get("chat"), expire_date = timedelta(minutes = 10))
                await query.message.answer(f'Ваша <a href="{invite_url.invite_link}">ссылка</a>. Она действительна только 10 минут', parse_mode = "html")
            else:
                await query.answer("Вы использовали 3 попытки.Попробуйте завтра", show_alert = True)
        case "get_invite_on_notion":
            user = session.query(User).filter_by(chat_id = query.from_user.id).first()
            for admin in admins:
                await bot.send_message(admin, f"Пользователь @{query.from_user.username} запросил инвайт на Notion на email: <strong>{user.email}</strong>", parse_mode = "html")

async def buy_subscription(query_or_message: types.CallbackQuery | types.Message, state: FSMContext):
    user = session.query(User).filter_by(chat_id = query_or_message.from_user.id).first()
    if not user.email:
        text = "Перед покупкой тарифа нужно установить email к Notion в личном кабинете"
        if isinstance(query_or_message, types.CallbackQuery):
            await query_or_message.message.answer(text, reply_markup = get_tarrifs_list_kb(True))
        else:
            await query_or_message.answer(text, reply_markup = get_tarrifs_list_kb(True))

    else:
        text = "Пожалуйста выберите длительность подписки ниже:"
        if isinstance(query_or_message, types.CallbackQuery):
            await query_or_message.message.answer(text, reply_markup = get_tarrifs_list_kb(True))
        else:
            await query_or_message.answer(text, reply_markup = get_tarrifs_list_kb(True))
        await state.set_state(UserStates.CHOOSE_TARIF)

async def process_promocode(message: types.Message, state: FSMContext):
    code = message.text.strip()
    promocode = session.query(Promocode).filter_by(code=code).first()

    if not promocode or promocode.activations_left <= 0:
        await message.answer("Промокод недействителен или уже использован.")
        await state.finish()
        return

    user = session.query(User).filter_by(chat_id=message.from_user.id).first()

    if promocode.type == 'Подписка':
        if user.subscription_to and user.subscription_to > datetime.now():
            user.subscription_to += timedelta(days=promocode.days)
        else:
            user.subscription_to = datetime.now() + timedelta(days=promocode.days)
        user.subscription_active = True
        await message.answer(f"Ваша подписка продлена до {user.subscription_to.strftime('%Y-%m-%d')}.")
    elif promocode.type == 'Скидка':
        user.promo_id = promocode.id
        await message.answer("Промокод успешно применен. Скидка будет учтена при оплате.")

    promocode.activations_left -= 1
    session.commit()
    await state.finish()


async def process_email(message: types.Message, state: FSMContext):
    email = message.text.strip()
    user = session.query(User).filter_by(chat_id=message.from_user.id).first()
    user.email = email
    session.commit()
    await message.answer("Ваш email для Notion успешно обновлен.")
    await state.finish()


async def select_tariff(query: types.CallbackQuery, state: FSMContext):
    tariff_id = int(query.data.split(':')[1])
    await state.set_data({"tariff_id": tariff_id})
    keyboard = types.InlineKeyboardMarkup()
    methods = session.query(PaymentMethod).all()
    for method in methods:
        button_text = f"{method.network}"
        callback_data = f"select_payment_method:{method.id}"
        keyboard.add(types.InlineKeyboardButton(button_text, callback_data=callback_data))
    keyboard.add(types.InlineKeyboardButton("Назад", callback_data="back_to_cabinet_menu"))
    await query.message.answer('Вибирите тариф:', reply_markup = keyboard)
    await state.set_state(UserStates.CHOOSE_METHOD)


async def select_method(query: types.CallbackQuery, state: FSMContext):
    method_id = int(query.data.split(':')[1])
    await state.update_data({"method_id": method_id})
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        types.InlineKeyboardButton("Оплатить", callback_data="procces_paynament"),
        types.InlineKeyboardButton("Назад", callback_data="back_to_cabinet_menu")
    ])
    await query.message.answer('Вы получаете доступ к следующим ресурсам: Дао, Нотион Дао', reply_markup = keyboard)


async def procces_paynament(query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    method = session.query(PaymentMethod).filter_by(id = data['method_id']).first()
    tariff = session.query(Tariffs).filter_by(id = data['tariff_id']).first()
    trans = Transaction(user_id = query.from_user.id, amount = tariff.amount, tariff_id = data['tariff_id'], method_id = data['method_id'], comfired = False, timestamp = datetime.now())
    session.add(trans)
    session.commit()
    
    user = session.query(User).filter_by(chat_id = query.from_user.id).first()
    promo = None
    if user.promo_id:
        promo = session.query(Promocode).filter_by(id = user.promo_id).first()
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        types.InlineKeyboardButton("Я оплатил", callback_data=f"proof_paynament:{trans.id}"),
    ])
    
    await query.message.answer(f"""
Способ оплаты: {method.network}
Адрес кошелька для оплаты: <pre>{method.wallet_address}</pre>
Сумма к оплате: {tariff.amount - tariff.amount * (promo.discount / 100) if promo else tariff.amount} usd
Промокод: {'Нет' if not promo else promo.code}
""", reply_markup = keyboard, parse_mode = "html")
    await state.finish()


async def proof_paynament(query: types.CallbackQuery, state: FSMContext):
    trans_id = int(query.data.split(':')[1])
    trans = session.query(Transaction).filter_by(id = trans_id).first()

    if not trans.comfired:
        await state.set_data({"trans_id": trans_id})
        await state.set_state(UserStates.SET_SCREENSHOT)
        await query.message.answer("""
Оплатили?
Тогда отправьте сюда, скриншот платежа либо хеш транзакции чтоб подтвердить ваш платеж.
""")


async def proof_paynament_text(message: types.Message, state: FSMContext):
    await state.update_data({"screen": message.photo[0]})
    await state.set_state(UserStates.SET_COMMENT)
    await message.answer('Отправте коментарий:')


async def give_for_checking(message: types.Message, state: FSMContext):
    data = await state.get_data()
    trans = session.query(Transaction).filter_by(id = data['trans_id']).first()
    method = session.query(PaymentMethod).filter_by(id = trans.method_id).first()
    tariff = session.query(Tariffs).filter_by(id = trans.tariff_id).first()
    user = session.query(User).filter_by(chat_id = trans.user_id).first()

    promo = None
    if user.promo_id:
        promo = session.query(Promocode).filter_by(id = user.promo_id).first()
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        types.InlineKeyboardButton("Подтвердить", callback_data=f"confirm_paynament:{trans.id}"),
        types.InlineKeyboardButton("Отклонить с комментарием", callback_data=f"cancle_paynament:{trans.id}"),  
    ])
    for admin in admins:
        await message.answer_photo(data["screen"], f"""
Способ оплаты: {admin}
Адрес кошелька для оплаты: <pre>{method.wallet_address}</pre>
Сумма к оплате: {tariff.amount - tariff.amount * (promo.discount / 100) if promo else tariff.amount} usd
Почта к Notion: <pre>{user.email}</pre>
Коментарий: {message.text}
Промокод: {'Нет' if not promo else promo.code}
""", reply_markup = keyboard, parse_mode = "html")


async def cancle_with_comment_paynament(query: types.CallbackQuery, state: FSMContext):
    trans_id = int(query.data.split(':')[1])
    await state.update_data({"trans_id": trans_id})
    await query.message.answer("Пожалуйста, введите причину отклонения платежа:")
    await state.set_state(UserStates.SET_COMMENT_ADMIN)

async def send_comment_to_user(message: types.Message, state: FSMContext):
    data = await state.get_data()
    trans_id = data['trans_id']
    trans = session.query(Transaction).filter_by(id=trans_id).first()
    user = session.query(User).filter_by(chat_id=trans.user_id).first()
    comment = message.text

    trans.comfired = False
    session.commit()
    await bot.send_message(
        user.id,
        f"Ваш платеж был отклонен. Причина: {comment}"
    )
    await message.answer("Платеж пользователя был отклонен.")
    await state.finish()

async def accept_paynament_comment_to_user(query: types.CallbackQuery, state: FSMContext):
    trans_id = int(query.data.split(':')[1])
    trans = session.query(Transaction).filter_by(id=trans_id).first()
    user = session.query(User).filter_by(chat_id=trans.user_id).first()

    trans.comfired = True
    session.commit()

    tariff = session.query(Tariffs).filter_by(id=trans.tariff_id).first()
    if user.subscription_to and user.subscription_to > datetime.now():
        user.subscription_to += relativedelta(months=tariff.months)
    else:
        user.subscription_to = datetime.now() + relativedelta(months=tariff.months)
    user.subscription_active = True
    if user.promo_id:
        user.promo_id = None
    session.commit()

    await bot.send_message(
        user.id,
        f"Ваш платеж был подтвержден. Ваша подписка активна до {user.subscription_to.strftime('%Y-%m-%d')}."
    )
    await query.message.answer("Платеж пользователя успешно был подтвержден.")
    await state.finish()


async def back_to_cabinet_menu(query: types.CallbackQuery, state: FSMContext):
    await state.finish()
    user = session.query(User).filter_by(id = query.from_user.id).first()
    sub_to: datetime = user.subscription_to
    await query.message.answer(f"""
Статистика:

Статус подписки: {user.subscription_active}    
Дата вступления: {user.subscription_from}
Дата окончания подписки {user.subscription_to}
Осталось еще {(sub_to - datetime.now()).days} к окончанию подписки
    """, get_user_panel_kb(user.subscription_active))
    await query.message.delete()

async def back_to_user_menu(query: types.CallbackQuery, state: FSMContext):
    await state.finish()
    keyboard_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard_markup.add(
        types.KeyboardButton("Личный кабинет"),
        types.KeyboardButton("Приобрести подписку"),
        types.KeyboardButton("Что такое Dao?"),
        types.KeyboardButton("Помощь")
    )
    await query.message.answer("Главное меню:", reply_markup = keyboard_markup)
    await query.message.delete()

def register_user(dp: Dispatcher):
    dp.register_callback_query_handler(process_user_menu, lambda cb: cb.data in ["buy_subscription", "use_promocode", "add_notion_email", "get_invite_on_tg", "get_invite_on_notion"], state = "*")
    dp.register_callback_query_handler(back_to_user_menu, lambda cb: cb.data == "back_to_user_menu", state = "*")
    dp.register_callback_query_handler(back_to_cabinet_menu, lambda cb: cb.data == "back_to_cabinet_menu", state = "*")
    dp.register_message_handler(buy_subscription, text = 'Приобрести подписку', state = "*")
    dp.register_callback_query_handler(select_tariff, state = UserStates.CHOOSE_TARIF)
    dp.register_callback_query_handler(select_method, state = UserStates.CHOOSE_METHOD)
    dp.register_callback_query_handler(procces_paynament, lambda cb: cb.data == 'procces_paynament')
    dp.register_callback_query_handler(proof_paynament, lambda cb: 'proof_paynament' in cb.data)
    dp.register_message_handler(proof_paynament_text, content_types = types.ContentTypes.PHOTO, state = UserStates.SET_SCREENSHOT)
    dp.register_message_handler(give_for_checking, state = UserStates.SET_COMMENT)
    dp.register_message_handler(process_promocode, state = UserStates.PROMOCODE)
    dp.register_message_handler(process_email, state = UserStates.ADD_EMAIL)
    dp.register_callback_query_handler(cancle_with_comment_paynament, lambda cb: 'cancle_paynament' in cb.data)
    dp.register_message_handler(send_comment_to_user, state=UserStates.SET_COMMENT_ADMIN)
    dp.register_callback_query_handler(accept_paynament_comment_to_user, lambda cb: 'confirm_paynament' in cb.data)