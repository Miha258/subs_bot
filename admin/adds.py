from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from datetime import datetime, timedelta
from db import User, session
import asyncio
from create_bot import bot, admins
import calendar
from keyboards import back_to_menu, launch_adds
from aiogram.dispatcher.filters.state import State, StatesGroup
import re

months = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
class SendInfo(StatesGroup):
    SET_TYPE = State()
    SET_MEDIA = State()
    SET_TEXT = State()
    SET_TIME = State()
    CONFIRM = State()


async def skip_media(message: types.Message):
    await SendInfo.next()
    await message.answer("Отправьте текст объявление:", reply_markup = back_to_menu())


async def proccess_new_add(message: types.Message, state: FSMContext):
    await state.finish()
    kb = types.ReplyKeyboardMarkup(keyboard = [
        [types.KeyboardButton("Отправить всем у кого есть подписка")],
        [types.KeyboardButton("Отправить абсолютно всем")],
        [types.KeyboardButton("Тем кто не продлил за 10 дней")],
        [types.KeyboardButton("Тем кто не продлил за 5 дней")],
        [types.KeyboardButton("Ни разу не платил")],
        [types.KeyboardButton("Тем кто купил и не продлил")]
    ])
    await message.answer('Вибирите тип:', reply_markup = kb)
    await state.set_state(SendInfo.SET_TYPE)


async def ask_for_media(message: types.Message, state: FSMContext):
    await state.update_data({'type': message.md_text})
    await state.set_state(SendInfo.SET_MEDIA)
    kb = back_to_menu()
    kb.add(types.KeyboardButton("Пропустить"))
    await message.answer("Отправьте фото/видео:", reply_markup = kb)


async def ask_for_text(message: types.Message, state: FSMContext):
    media = message.photo[0] if message.photo else message.video

    await state.update_data({'media': media})
    await state.set_state(SendInfo.SET_TEXT)
    await message.reply("Отправьте текст объявление:", reply_markup = back_to_menu())


def get_calendar(month: int = 0):
    inline_markup = types.InlineKeyboardMarkup(row_width=7)
    date = datetime.today()

    if month < 0:
        date = date.replace(year = date.year + 1) 

    start = 1 if month else date.day
    end = calendar.monthrange(date.year, date.month + month)[1]
    for day in range(start, end + 1):
        inline_markup.insert(types.InlineKeyboardButton(str(day), callback_data = f"calendar_day:{date.year}-{date.month + month}-{day}"))

    inline_markup.row(
        types.InlineKeyboardButton(" ← ", callback_data = "prev_month"),
        types.InlineKeyboardButton(months[date.month + month - 1], callback_data = "current_month"),
        types.InlineKeyboardButton(" → ", callback_data = "next_month")
    )
    inline_markup.add(types.InlineKeyboardButton("Опубликовать уже", callback_data = "confirm_sending"))
    return inline_markup

  
async def set_calendar_month(callback_query: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        index = data.get("calendar") if data.get("calendar") else 0
        add = index + 1 if callback_query.data == "next_month" else index - 1
        data["calendar"] = add
        await callback_query.message.edit_reply_markup(get_calendar(add))
    

async def choose_date(callback_query: types.CallbackQuery, state: FSMContext):
    date = callback_query.data.split(":")[1]
    await state.update_data({"date": date})
    await callback_query.answer("Вибирите дату:")


async def ask_for_time(message: types.Message, state: FSMContext):
    await state.update_data({"text": message.text})
    await state.set_state(SendInfo.SET_TIME)
    await message.answer("Теперь виберите время отправки объявление.Потом введите время в формате <strong>HH:MM</strong>", reply_markup = get_calendar(), parse_mode = "html")


async def send_adds_to_users(query: types.CallbackQuery, state: FSMContext):
    
    async with state.proxy() as data: 
        text = data.get('text')
        media = data.get('media')
        adds_type = data.get('type')
        current_date = datetime.now()
        match adds_type:
            case "Отправить всем у кого есть подписка":
                users = session.query(User).filter(User.subscription_active == True).all()
            case "Отправить абсолютно всем":
                users = session.query(User).all()
            case "Тем кто не продлил за 10 дней":
                users = session.query(User).filter(User.subscription_active == False,
                                    User.subscription_to < current_date - timedelta(days=10)).all()
            case "Тем кто не продлил за 5 дней":
                users = session.query(User).filter(User.subscription_active == False,
                                    User.subscription_to < current_date - timedelta(days=5)).all()
            case "Ни разу не платил":
                users = session.query(User).filter(User.subscription_to == None).all()
            case "Тем кто купил и не продлил":
                users = session.query(User).filter(User.subscription_active == False,
                                    User.subscription_from != None).all()

        counter = 0
        for user in users:
            try:
                if media:
                    match type(media):
                        case types.PhotoSize:
                            await bot.send_photo(user.chat_id, photo = media.file_id, caption = text)
                        case types.Video:
                            await bot.send_video(user.chat_id, video = media.file_id, caption = text)
                else:
                    await bot.send_message(user.chat_id, text)
                counter += 1
            except:
                pass
        await query.message.answer(f"""
Тип рассылки: <strong>{adds_type}</strong>
Потенциальное количество: <strong>{len(users)}</strong>
Отправлено: <strong>{counter}</strong>
        """, parse_mode = "html", reply_markup = types.ReplyKeyboardRemove())
        await state.finish()
   

async def send_message_with_delay(query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    while datetime.now() < data['datetime']: await asyncio.sleep(1)
    await send_adds_to_users(query, state)

async def send_confirm_adds(message_or_query: types.Message, state: FSMContext):
    
    async with state.proxy() as data:
        if isinstance(message_or_query, types.CallbackQuery):
            await message_or_query.message.answer("Подтвердите действия:", reply_markup = launch_adds())
        else:
            date_time_regex = r'\d{2}:\d{2}'
            if re.search(date_time_regex, message_or_query.text): 
                date_obj = datetime.strptime(data.get('date'), "%Y-%m-%d")
                time_obj = datetime.strptime(message_or_query.text, "%H:%M")
                date = datetime.combine(date_obj.date(), time_obj.time())
                date["datetime"] = message_or_query.text
                await message_or_query.answer("Подтвердите действия:", reply_markup = launch_adds(True))
    await state.set_state(SendInfo.CONFIRM)

def register_adds(dp: Dispatcher):
    dp.register_message_handler(proccess_new_add, lambda m: m.from_id in admins, text = 'Сделать рассылку', state = "*")
    dp.register_message_handler(ask_for_media, state = SendInfo.SET_TYPE)
    dp.register_message_handler(ask_for_text, state = SendInfo.SET_MEDIA, content_types = [types.ContentType.PHOTO, types.ContentType.VIDEO])
    dp.register_message_handler(skip_media, lambda m: m.text in "Пропустить", state = SendInfo.SET_MEDIA)
    dp.register_callback_query_handler(choose_date, lambda cb: "calendar_day" in cb.data, state = SendInfo.SET_TIME)
    dp.register_callback_query_handler(set_calendar_month, lambda cb: cb.data in ["prev_month", "next_month"], state = SendInfo.SET_TIME)
    dp.register_callback_query_handler(send_confirm_adds, lambda cb: cb.data == "confirm_sending", state = SendInfo.SET_TIME)
    dp.register_message_handler(ask_for_time, state = SendInfo.SET_TEXT)
    dp.register_message_handler(send_confirm_adds, state = SendInfo.SET_TIME)
    dp.register_callback_query_handler(send_adds_to_users, lambda cb: cb.data == "launch_adds_sending", state = SendInfo.CONFIRM)
    dp.register_callback_query_handler(send_message_with_delay, lambda cb: cb.data == "launch_adds_sending_with_delay", state = SendInfo.CONFIRM)