from db import session, User
from create_bot import bot, admins
from datetime import timedelta
from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

class SubsStates(StatesGroup):
    SUBS_COUNT = State()

async def set_subs(message: types.Message, state: FSMContext):
    await message.answer('Введите количство дней:')
    await state.set_state(SubsStates.SUBS_COUNT)

async def extend_subscriptions(message: types.Message, state: FSMContext):
    try:
        days_to_add = int(message.text)
        users = session.query(User).all()
        for user in users:
            user.subscription_to = user.subscription_to + timedelta(days = days_to_add)
            session.commit()
            await bot.send_message(user.chat_id, f"Ваша подписка продлена на {days_to_add} дней!")
        await state.finish()
    except ValueError:
        await message.answer("Введите число:")


def register_subs(dp: Dispatcher):
    dp.register_message_handler(set_subs, lambda m: m.from_id in admins, text = "Продлить подписку", state = "*")
    dp.register_message_handler(extend_subscriptions, state = SubsStates.SUBS_COUNT)