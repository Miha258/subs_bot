import logging
from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram import executor
from scheduler import Scheduler
import asyncio, time
from db import session, User
import datetime as dt
from create_bot import bot, dp, admins
from admin.promocodes import register_promo
from admin.paynaments import register_payment_methods
from admin.adds import register_adds
from admin.subs import register_subs
from admin.settings import register_settins
from admin.tariffs import register_tariffs
from admin.stats import register_stats
from user import register_user
from keyboards import *
from admin.utils import load_config
import threading

logging.basicConfig(level=logging.INFO)
schedule = Scheduler()

@dp.message_handler(commands=['start'], state = "*")
async def cmd_start(message: types.Message):
    user = session.query(User).filter_by(chat_id=message.from_id).first()
    if not user:
        user = User(chat_id = message.chat.id)
        session.add(user)
        session.commit()
    await send_welcome_message(message)
    

async def send_welcome_message(message: types.Message):
    keyboard_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard_markup.add(
        types.KeyboardButton("Личный кабинет"),
        types.KeyboardButton("Приобрести подписку"),
        types.KeyboardButton("Что такое Dao?"),
        types.KeyboardButton("Помощь")
    )
    if message.from_id in admins:
        keyboard_markup.add(types.KeyboardButton("Админ панель"))
    await message.answer(
"""
🔥 Добро пожаловать в Приватный Клуб! 🔥

Ты когда-нибудь задумывался, почему, несмотря на все твои усилия, что-то в этом мире кажется не таким, как должно быть?
Эта навязчивая мысль не дает тебе покоя, она толкает тебя искать ответы. 
И вот ты здесь. Да, ты уже на пороге чего-то великого.
Если человек владеет информацией, то он владеет миром! 
Это не просто слова, это наш кредо. В Приватном Клубе Алькриптоне ты обретешь мощь истинных знаний, которые откроют тебе глаза на мир таким, каким ты его еще не видел.
Сделай выбор, который может раз и навсегда изменить твою жизнь. 

<strong>Ты с нами?</strong>

💥 Присоединяйся сейчас и возьми свою судьбу в свои руки! 💥
""",
        reply_markup=keyboard_markup,
        parse_mode = "html"
    )


@dp.message_handler(lambda m: m.text == "Личный кабинет", state="*")
async def process_personal_cabinet(message: types.Message, state: FSMContext):
    await state.finish()
    user = session.query(User).filter_by(chat_id=message.from_id).first()
    if not user:
        return
    
    if not user.subscription_from or not user.subscription_to:
        return await message.answer("Чтобы использовать это меню нужно приобрести подписку")

    sub_to: dt.datetime = user.subscription_to
    if sub_to:
        text = f"""
Статистика:

Статус подписки: <strong>{"неактивна" if not user.subscription_active else "активна"}</strong>    
Дата вступления: <strong>{user.subscription_from.strftime('%Y-%m-%d') if user.subscription_from else "нет"}</strong>
Дата окончания подписки: <strong>{user.subscription_to.strftime('%Y-%m-%d') if user.subscription_to else "нет"}</strong>
Осталось еще <strong>{(sub_to - dt.datetime.now()).days}</strong> дней к окончанию подписки
"""
    else:
        text = f"""
Статистика:

Статус подписки: <strong>{"неактивна" if not user.subscription_active else "активна"}</strong>    
Дата вступления: <strong>{user.subscription_from.strftime('%Y-%m-%d') if user.subscription_from else "нет"}</strong>
Дата окончания подписки: <strong>{user.subscription_to.strftime('%Y-%m-%d') if user.subscription_to else "нет"}</strong>
"""
    await message.answer(text, reply_markup=get_user_panel_kb(user.subscription_active), parse_mode = "html")

@dp.message_handler(lambda m: m.text == "Что такое Dao?", state="*")
async def process_what_is_dao(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("""
В нашем DAO мы работаем круглосуточно, исследуя информационное пространство интернета, чтобы предоставить вам доступ к эксклюзивному и высококачественному контенту. Это позволяет вам экономить каждую секунду вашего времени. Наш слоган гласит: "Если ты владеешь информацией, ты владеешь миром!"
Чего у нас нет?
Важно отметить: в нашем DAO нет места трейдингу и всему, что с этим связано. За скамом и быстрыми схемами заработка — пожалуйста, обращайтесь в другие проекты. У нас все заработано честно: чем больше усилий, тем больше доход. У нас нет места легким деньгам и автоматическим заработкам. Ваша жизнь — ваше творение, а наша задача — обеспечить вас нужной информацией.
Наши особенности:
1- Ретродропы
2- NFT-флипы/колы и выбивание вайтлистов
3 - Амбассадорские программы
4 - Тестнеты
5 - Аналитика крипторынка
6 - Прочие активности в мире криптовалюты, на которых
можно заработать
В нашем DAO вы обнаружите уникальные возможности, доступ к которым открывается на самых ранних этапах проектов. Это время, когда конкуренция минимальна, а потенциал для заработка — наивысший. Присоединяйтесь к нам, чтобы вместе исследовать и использовать возможности, предоставляемые криптовалютным миром!
""")

@dp.message_handler(lambda m: m.text == "Помощь", state="*")
async def process_help(message: types.Message, state: FSMContext):
    await state.finish()
    config = load_config()
    await message.answer(f"В данном разделе вы можете задать помощь и очень скоро получить ответ по любому своему вопросу!\nКонтакт для связи: {config['support']}")


@dp.message_handler(lambda m: m.from_id in admins, text = 'Админ панель', state = "*")
async def open_admin(message: types.Message):
    await message.answer('Меню администратора:', reply_markup = get_main_admin_menu_kb())


@dp.message_handler(lambda m: m.from_id in admins and m.text == 'Назад', state = "*")
async def back_to_main_admin_menu(message: types.Message, state: FSMContext):
    await state.finish()
    await message.delete()
    await message.answer('Меню администратора:', reply_markup = get_main_admin_menu_kb())


@dp.callback_query_handler(lambda cb: cb.data == "back_to_main_admin_menu", state = "*")
async def back_to_main_admin_menu(query: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await query.message.delete()
    await query.message.answer('Меню администратора:', reply_markup = get_main_admin_menu_kb())
    


async def on_startup(dp):
    threading.Thread(target = lambda: run_tasks()).start()
    await bot.set_my_commands([
        types.BotCommand("start", "Начать работу с ботом")
    ])


def update_retries():
    users = session.query(User).all()
    for user in users:
        user.invite_link_retries = 3
        session.commit()


async def check_subscription():
    config = load_config()
    chat = config.get('chat')
    if chat:
        users = session.query(User).filter_by(subscription_active = True).all()
        if users:
            try:
                for user in users:
                    is_in_chat = await bot.get_chat_member(chat, user.id)
                    if user.subscription_to < dt.datetime.now() and is_in_chat:
                        await bot.kick_chat_member(chat, user.id)
                        for admin in admins:
                            try:
                                tg_user = await bot.get_chat(user.chat_id)
                                await bot.send_message(admin, f"У @{tg_user.username} закончилась подписка.Почта: <strong>{user.email}</strong>.Нужно удалить из Notion", parse_mode = "html")
                            except Exception:
                                await bot.send_message(admin, f"У пользователя закончилась подписка.Почта: <strong>{user.email}</strong>.Нужно удалить из Notion", parse_mode = "html")
            except Exception as e:
                print(e)

schedule.daily(dt.time(hour = 23, minute=59), update_retries)
schedule.minutely(dt.time(minute = 1), lambda: asyncio.run(check_subscription()))

def run_tasks():
    while True:
        schedule.exec_jobs()
        time.sleep(1)


if __name__ == '__main__':
    register_promo(dp)
    register_payment_methods(dp)
    register_adds(dp)
    register_subs(dp)
    register_settins(dp)
    register_stats(dp)
    register_tariffs(dp)
    register_user(dp)
    executor.start_polling(dp, on_startup=on_startup)
