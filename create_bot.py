from aiogram import Bot, Dispatcher
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.contrib.fsm_storage.memory import MemoryStorage
import os, dotenv


dotenv.load_dotenv()

bot = Bot(token = os.environ.get("TOKEN"))
storage = MemoryStorage()
dp = Dispatcher(bot, storage = storage)
dp.middleware.setup(LoggingMiddleware())
admins = [1095610815, 5373411827, 6070540248]