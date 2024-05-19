from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.contrib.fsm_storage.memory import MemoryStorage

bot = Bot(token="7036992400:AAFSlvRteAqk4ZHTGvq2VzJWPDOmKQjdmi4")
storage = MemoryStorage()
dp = Dispatcher(bot, storage = storage)
dp.middleware.setup(LoggingMiddleware())
admins = [1095610815, 5373411827]