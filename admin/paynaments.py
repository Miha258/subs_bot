from db import session, PaymentMethod
from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from create_bot import admins

class PaymentMethodCreation(StatesGroup):
    NETWORK = State()
    WALLET_ADDRESS = State()


class EditPaymentMethodState(StatesGroup):
    EDITING = State()
    WALLET_ADDRESS = State()


def get_edit_payment_method_kb(method: PaymentMethod):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton("Редактировать адрес", callback_data=f"edit_method_address:{method.id}")
    )
    keyboard.add(
        types.InlineKeyboardButton("Удалить метод", callback_data=f"delete_method:{method.id}")
    )
    keyboard.add(
        types.InlineKeyboardButton("Назад", callback_data="back_to_payment_methods")
    )
    return keyboard



async def view_payment_methods(message: types.Message, state: FSMContext, _return = False):
    await state.finish()
    payment_methods = session.query(PaymentMethod).all()
    keyboard = types.InlineKeyboardMarkup()

    if payment_methods:
        for method in payment_methods:
            button_text = f"{method.network}: {method.wallet_address}"
            callback_data = f"edit_payment_method:{method.id}"
            keyboard.add(types.InlineKeyboardButton(button_text, callback_data=callback_data))
        keyboard.add(types.InlineKeyboardButton("Добавить метод оплаты", callback_data="add_payment_method"))
        if _return:
            return "Вибирете метод оплаты для редактирования:", keyboard
        await message.answer("Вибирете метод оплаты для редактирования:", reply_markup=keyboard)
    else:
        keyboard.add(types.InlineKeyboardButton("Добавить метод оплаты", callback_data="add_payment_method"))
        
        if _return:
            return "Пока нету методов оплаты.Добавьте первый метод оплаты:", keyboard
        await message.answer("Пока нету методов оплаты.Добавьте первый метод оплаты:", reply_markup=keyboard)


async def start_payment_method_creation(query: types.CallbackQuery, state: FSMContext):
    await query.message.answer("Введите название сети (например, USDT TRC20):")
    await PaymentMethodCreation.NETWORK.set()


async def process_network(message: types.Message, state: FSMContext):
    network = message.text
    await state.update_data({"network": network})
    await message.answer("Введите адрес кошелька:")
    await PaymentMethodCreation.WALLET_ADDRESS.set()


async def process_wallet_address(message: types.Message, state: FSMContext):
    wallet_address = message.text
    await state.update_data({"wallet_address": wallet_address})
    data = await state.get_data()

    payment_method = PaymentMethod(network = data["network"], wallet_address = data["wallet_address"])
    session.add(payment_method)
    session.commit()
    await message.answer(f"Способ оплаты <strong>{data['network']}</strong> успешно создан!", parse_mode = "html")
    await view_payment_methods(message, state)
    await state.finish()


async def edit_payment_method(query: types.CallbackQuery, state: FSMContext):
    method_id = int(query.data.split(':')[1])
    method = session.query(PaymentMethod).filter_by(id=method_id).first()
    msg = await query.message.answer(
        f'Редактирование метода оплаты:\nСеть: {method.network}\nАдрес кошелька: {method.wallet_address}',
        reply_markup=get_edit_payment_method_kb(method)
    )
    await state.set_data({"target_msg": msg})
    await state.set_state(EditPaymentMethodState.EDITING)

async def edit_payment_method_handler(query: types.CallbackQuery, state: FSMContext):
    edit_action = query.data.split(':')[0]
    method_id = int(query.data.split(':')[1])
    await state.update_data({"method_id": method_id})
    
    match edit_action:
        case "delete_method":
            await delete_payment_method(query, state)
        case "edit_method_address":
            await query.message.answer('Введите новый адрес кошелька:')
            await state.set_state(EditPaymentMethodState.WALLET_ADDRESS)

async def edit_method_address(message: types.Message, state: FSMContext):
    data = await state.get_data()
    method_id = data["method_id"]
    method = session.query(PaymentMethod).filter_by(id=method_id).first()
    try:
        new_address = message.text
        method.wallet_address = new_address
        session.commit()
        await state.finish()
        await message.delete()
        target_msg = data["target_msg"]
        await target_msg.edit_reply_markup(get_edit_payment_method_kb(method))
    except ValueError:
        await message.answer("Пожалуйста, введите действительный адрес кошелька.")


async def delete_payment_method(query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    method_id = data["method_id"]
    method = session.query(PaymentMethod).filter_by(id=method_id).first()
    session.delete(method)
    session.commit()
    await view_payment_methods(query.message, state)


async def back_to_payment_methods_list(query: types.CallbackQuery, state: FSMContext):
    text, kb = await view_payment_methods(query.message, state, True)
    await query.message.edit_text(text, reply_markup = kb)


def register_payment_methods(dp: Dispatcher):
    dp.register_message_handler(view_payment_methods, lambda m: m.from_id in admins, text = 'Способы оплаты', state = "*")
    dp.register_callback_query_handler(back_to_payment_methods_list, lambda cb: cb.data == 'back_to_payment_methods', state = "*")
    dp.register_callback_query_handler(edit_payment_method, lambda cb: "edit_payment_method" in cb.data)
    dp.register_callback_query_handler(edit_payment_method_handler, state= EditPaymentMethodState.EDITING)
    dp.register_message_handler(edit_method_address, state= EditPaymentMethodState.WALLET_ADDRESS)
    dp.register_callback_query_handler(delete_payment_method, lambda cb: cb.data.startswith("delete_method"))


    dp.register_callback_query_handler(start_payment_method_creation, lambda cb: cb.data == 'add_payment_method')
    dp.register_message_handler(process_network, state=PaymentMethodCreation.NETWORK)
    dp.register_message_handler(process_wallet_address, state=PaymentMethodCreation.WALLET_ADDRESS)