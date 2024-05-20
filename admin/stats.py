from aiogram import types, Dispatcher
from db import session, User, Transaction
from sqlalchemy import func
from datetime import datetime, timedelta
from create_bot import admins


async def get_stats(message: types.Message):
    active_subscribers = session.query(func.count(User.id)).filter(User.subscription_active == True).scalar()
    active_users = session.query(func.count(User.id)).scalar()
    subscribers_expiring_soon = session.query(func.count(User.id)).filter(User.subscription_to <= datetime.now() + timedelta(days=5)).scalar()
    current_month_income = session.query(func.sum(Transaction.amount)).filter(func.strftime('%Y-%m', Transaction.timestamp) == datetime.now().strftime('%Y-%m')).scalar()
    total_income = session.query(func.sum(Transaction.amount)).scalar()
    stats_message = (
        f"Количество активных пользователей с подпиской: <strong>{active_subscribers}</strong>\n"
        f"Количество пользователей, у которых запущен бот: <strong>{active_users}</strong>\n"
        f"Количество пользователей, у которых подписка заканчивается через 5 дней: <strong>{subscribers_expiring_soon}</strong>\n"
        f"Доход за текущий месяц: <strong>{current_month_income if current_month_income else '0'}</strong>\n"
        f"Доход за все время: <strong>{total_income if total_income else '0'}</strong>\n"
    )
    await message.answer(stats_message, parse_mode = "html")

def register_stats(dp: Dispatcher):
    dp.register_message_handler(get_stats, lambda m: m.from_id in admins, text = 'Статистика', state = "*")