from db import session, Tariffs
from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

class TariffsCreationState(StatesGroup):
    AMOUNT = State()
    MONTHS = State()


class EditTariffsState(StatesGroup):
    EDITING = State()
    AMOUNT = State()
    MONTHS = State()


def get_edit_tariff_kb(tariff: Tariffs):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton("Редактировать количество месяцев", callback_data=f"edit_tariff_months:{tariff.id}")
    )
    keyboard.add(
        types.InlineKeyboardButton("Редактировать цену", callback_data=f"edit_tariff_amount:{tariff.id}")
    )
    keyboard.add(
        types.InlineKeyboardButton("Удалить", callback_data=f"delete_tariff:{tariff.id}")
    )
    keyboard.add(
        types.InlineKeyboardButton("Назад", callback_data="back_to_tariffs_list")
    )
    return keyboard

def get_tarrifs_list_kb(select = False):
    tariffs = session.query(Tariffs).all()
    keyboard = types.InlineKeyboardMarkup()
    if tariffs:
        for tariff in tariffs:
            months_text = ""
            if tariff.months == 1:
                months_text = 'месец'
            elif tariff.months == 2 or tariff.months == 3:
                months_text = 'месяца'
            else:
                months_text = 'месяцев'

            button_text = f"{tariff.months} {months_text}/{tariff.amount} usd"
            callback_data =  f"select_tariff:{tariff.id}" if select else f"edit_tariff:{tariff.id}"
            keyboard.add(types.InlineKeyboardButton(button_text, callback_data=callback_data))
        if select:
            keyboard.add(types.InlineKeyboardButton(button_text, callback_data="back_to_cabinet_menu"))
    return keyboard

async def view_tariffs(message: types.Message, state: FSMContext, _return = False):
    await state.finish()
    keyboard = get_tarrifs_list_kb()
    keyboard.add(types.InlineKeyboardButton("Добавить тариф", callback_data="add_tariff"))
    if len(keyboard.inline_keyboard) == 1:
        if _return:
            return "Пока нету тарифов.Добавьте первый тариф:", keyboard
        await message.answer("Пока нету тарифов.Добавьте тариф:", reply_markup=keyboard)
    else:
        if _return:
            return "Вибирете тариф для редактирования:", keyboard
        await message.answer("Вибирете тариф для редактирования:", reply_markup=keyboard)
        
        
       


async def start_tariff_creation(query: types.CallbackQuery, state: FSMContext):
    await query.message.answer("Введите цену в usd:")
    await state.set_state(TariffsCreationState.AMOUNT)


async def process_amount(message: types.Message, state: FSMContext):
    try:
        amount = int(message.text)
        await state.set_data({"amount": amount})
        await message.answer("Введите количество месяцев:")
        await state.set_state(TariffsCreationState.MONTHS)
    except ValueError:
        await message.answer('Введите число:')


async def process_months(message: types.Message, state: FSMContext):
    try:
        months = int(message.text)
        data = await state.get_data()

        tariff = Tariffs(amount = data["amount"], months = months)
        session.add(tariff)
        session.commit()
        await message.answer(f"Тариф успешно создан!", parse_mode = "html")
        await view_tariffs(message, state)
        await state.finish()
    except ValueError:
        await message.answer("Введите число:")


async def edit_tariff(query: types.CallbackQuery, state: FSMContext):
    tariff_id = int(query.data.split(':')[1])
    tariff = session.query(Tariffs).filter_by(id=tariff_id).first()
    msg = await query.message.answer(
        f'Редактирование тарифа:\nЦена: {tariff.amount} usd\nКоличество месяцев: {tariff.months}',
        reply_markup=get_edit_tariff_kb(tariff)
    )
    await state.set_data({"target_msg": msg})
    await state.set_state(EditTariffsState.EDITING)


async def edit_tariff_handler(query: types.CallbackQuery, state: FSMContext):
    edit_action = query.data.split(':')[0]
    tariff_id = int(query.data.split(':')[1])
    await state.update_data({"tariff_id": tariff_id})
    
    match edit_action:
        case "delete_tariff":
            await delete_tariff(query, state)
        case "edit_tariff_amount":
            await query.message.answer('Введите цену тарифа в usd:')
            await state.set_state(EditTariffsState.AMOUNT)
        case "edit_tariff_months":
            await query.message.answer('Введите количество месецев:')
            await state.set_state(EditTariffsState.MONTHS)

async def edit_tariff_amount(message: types.Message, state: FSMContext):
    data = await state.get_data()
    tariff_id = data["tariff_id"]
    tariff = session.query(Tariffs).filter_by(id=tariff_id).first()
    try:
        new_amount = int(message.text)
        tariff.amount = new_amount
        session.commit()
        await state.finish()
        await message.delete()
        target_msg = data["target_msg"]
        await target_msg.edit_reply_markup(get_edit_tariff_kb(tariff))
    except ValueError:
        await message.answer("Введите число:")


async def delete_tariff(query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    tariff_id = data["tariff_id"]
    tariff = session.query(Tariffs).filter_by(id=tariff_id).first()
    session.delete(tariff)
    session.commit()
    await view_tariffs(query.message, state)


async def edit_tariff_months(message: types.Message, state: FSMContext):
    data = await state.get_data()
    tariff_id = data["tariff_id"]
    tariff = session.query(Tariffs).filter_by(id=tariff_id).first()
    try:
        months = int(message.text)
        tariff.months = months
        session.commit()
        await state.finish()
        await message.delete()
        target_msg = data["target_msg"]
        await target_msg.edit_text(
        f'Редактирование тарифа:\nЦена: {tariff.amount} usd\nКоличество месяцев: {tariff.months}',
        reply_markup=get_edit_tariff_kb(tariff)
    )
    except ValueError:
        await message.answer("Пожалуйста, введите действительный адрес кошелька.")


async def back_to_tariffs_list(query: types.CallbackQuery, state: FSMContext):
    text, kb = await view_tariffs(query.message, state, True)
    await query.message.edit_text(text, reply_markup = kb)


def register_tariffs(dp: Dispatcher):
    dp.register_message_handler(view_tariffs, text = 'Управлять тарифами', state = "*")
    dp.register_callback_query_handler(back_to_tariffs_list, lambda cb: cb.data == 'back_to_tariffs_list', state = "*")
    dp.register_callback_query_handler(edit_tariff, lambda cb: "edit_tariff" in cb.data)
    dp.register_callback_query_handler(edit_tariff_handler, state= EditTariffsState.EDITING)
    dp.register_message_handler(edit_tariff_amount, state = EditTariffsState.AMOUNT)
    dp.register_message_handler(edit_tariff_months, state = EditTariffsState.MONTHS)
    dp.register_callback_query_handler(delete_tariff, lambda cb: cb.data.startswith("delete_tariff"))

    dp.register_callback_query_handler(start_tariff_creation, lambda cb: cb.data == 'add_tariff')
    dp.register_message_handler(process_amount, state=TariffsCreationState.AMOUNT)
    dp.register_message_handler(process_months, state=TariffsCreationState.MONTHS)