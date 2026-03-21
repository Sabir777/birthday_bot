"""Telegram-бот для напоминания о днях рождениях коллег"""

import asyncio
import logging
from datetime import datetime
from typing import Optional

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import BOT_TOKEN, CHAT_ID, NOTIFICATION_TIME
from database import Database

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Инициализация
db = Database()
bot: Optional[Bot] = None
scheduler: Optional[AsyncIOScheduler] = None


class AddColleague(StatesGroup):
    """Состояния для процесса добавления коллеги"""
    waiting_for_name = State()
    waiting_for_date = State()


class DeleteColleague(StatesGroup):
    """Состояния для процесса удаления коллеги"""
    waiting_for_id = State()


async def send_birthday_notifications(bot: Bot):
    """Отправка уведомлений о днях рождениях"""
    today = datetime.now()
    colleagues = db.get_colleagues_by_date(today.month, today.day)
    
    if colleagues:
        names = [name for _, name in colleagues]
        message = "🎉 "
        if len(names) == 1:
            message += f"Сегодня день рождения у {names[0]}! Поздравляем! 🎂🎈"
        else:
            message += f"Сегодня день рождения у: {', '.join(names)}! Поздравляем! 🎂🎈"
        
        # Получаем ID чата из настроек
        settings = db.get_chat_settings()
        target_chat_id = CHAT_ID
        
        if settings:
            target_chat_id = settings[1]
        
        if target_chat_id:
            try:
                await bot.send_message(target_chat_id, message)
                logger.info(f"Отправлено уведомление о ДР в чат {target_chat_id}")
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления: {e}")
        else:
            logger.warning("CHAT_ID не настроен, пропускаем уведомление")


async def start_command(message: types.Message):
    """Обработчик команды /start"""
    await message.answer(
        "👋 Привет! Я бот для напоминания о днях рождениях коллег.\n\n"
        "📋 **Доступные команды:**\n"
        "/add — добавить коллегу\n"
        "/list — показать всех коллег\n"
        "/delete — удалить коллегу\n"
        "/help — подробная справка\n\n"
        "Добавьте меня в групповой чат, и я буду напоминать о днях рождениях! 🎉"
    )


async def help_command(message: types.Message):
    """Обработчик команды /help"""
    await message.answer(
        "📖 **Инструкция по использованию бота**\n\n"
        "**🔧 Настройка:**\n"
        "1. Добавьте бота в групповой чат\n"
        "2. Дайте права на отправку сообщений\n\n"
        "**📝 Добавление коллеги:**\n"
        "1. Отправьте /add\n"
        "2. Введите имя коллеги\n"
        "3. Введите дату рождения в формате ДД.ММ (например, 15.05)\n\n"
        "**📋 Просмотр списка:**\n"
        "Отправьте /list для просмотра всех коллег с датами рождения\n\n"
        "**❌ Удаление коллеги:**\n"
        "1. Отправьте /delete\n"
        "2. Введите ID коллеги из списка\n\n"
        "**⏰ Уведомления:**\n"
        "Бот отправляет сообщения каждое утро в 09:00 UTC в день рождения коллеги"
    )


async def add_command(message: types.Message, state: FSMContext):
    """Обработчик команды /add"""
    await message.answer("📝 Введите **имя коллеги**:", parse_mode="Markdown")
    await state.set_state(AddColleague.waiting_for_name)


async def process_name(message: types.Message, state: FSMContext):
    """Обработка имени коллеги"""
    name = message.text.strip()
    if not name:
        await message.answer("⚠️ Пожалуйста, введите корректное имя:")
        return
    
    await state.update_data(name=name)
    await message.answer(
        f"✅ Имя сохранено: **{name}**\n\n"
        "Теперь введите **дату рождения** в формате ДД.ММ (например, 15.05):",
        parse_mode="Markdown"
    )
    await state.set_state(AddColleague.waiting_for_date)


async def process_date(message: types.Message, state: FSMContext):
    """Обработка даты рождения"""
    date_text = message.text.strip()
    
    # Проверка формата даты
    try:
        day, month = map(int, date_text.split("."))
        if not (1 <= day <= 31 and 1 <= month <= 12):
            raise ValueError()
    except (ValueError, AttributeError):
        await message.answer(
            "⚠️ Неверный формат даты. Используйте формат **ДД.ММ** (например, 15.05):",
            parse_mode="Markdown"
        )
        return
    
    # Получаем данные из состояния
    data = await state.get_data()
    name = data["name"]
    
    # Добавляем в базу данных
    if db.add_colleague(name, date_text):
        await message.answer(
            f"🎉 Коллега **{name}** добавлен(а)!\n"
            f"День рождения: {date_text}",
            parse_mode="Markdown"
        )
    else:
        await message.answer("❌ Произошла ошибка при добавлении. Попробуйте еще раз.")
    
    await state.clear()


async def list_command(message: types.Message):
    """Обработчик команды /list"""
    colleagues = db.get_all_colleagues()
    
    if not colleagues:
        await message.answer("📭 Список коллег пока пуст. Добавьте первого коллегу командой /add")
        return
    
    response = "📋 **Список коллег:**\n\n"
    for col_id, name, month, day in colleagues:
        # Названия месяцев
        months = [
            "", "января", "февраля", "марта", "апреля", "мая", "июня",
            "июля", "августа", "сентября", "октября", "ноября", "декабря"
        ]
        response += f"**ID {col_id}**: {name} — {day} {months[month]}\n"
    
    await message.answer(response, parse_mode="Markdown")


async def delete_command(message: types.Message, state: FSMContext):
    """Обработчик команды /delete"""
    colleagues = db.get_all_colleagues()
    
    if not colleagues:
        await message.answer("📭 Список коллег пуст. Нечего удалять.")
        return
    
    response = "❌ **Удаление коллеги**\n\n"
    response += "Текущий список:\n"
    for col_id, name, month, day in colleagues:
        response += f"**ID {col_id}**: {name} — {day}.{month:02d}\n"
    
    response += "\nВведите **ID** коллеги для удаления:"
    
    await message.answer(response, parse_mode="Markdown")
    await state.set_state(DeleteColleague.waiting_for_id)


async def process_delete_id(message: types.Message, state: FSMContext):
    """Обработка ID для удаления"""
    try:
        colleague_id = int(message.text.strip())
    except ValueError:
        await message.answer("⚠️ Введите корректный числовой ID:")
        return
    
    colleague = db.get_colleague_by_id(colleague_id)
    
    if colleague:
        if db.delete_colleague(colleague_id):
            await message.answer(
                f"✅ Коллега **{colleague[1]}** удален(а) из списка.",
                parse_mode="Markdown"
            )
        else:
            await message.answer("❌ Ошибка при удалении. Попробуйте еще раз.")
    else:
        await message.answer("⚠️ Коллега с таким ID не найден.")
    
    await state.clear()


async def setup_chat_command(message: types.Message):
    """Обработчик команды /setup_chat для настройки чата"""
    chat_id = str(message.chat.id)
    db.save_chat_settings(chat_id)
    await message.answer(
        f"✅ Чат настроен! ID: {chat_id}\n"
        "Теперь бот будет отправлять уведомления о днях рождениях в этот чат."
    )
    logger.info(f"Настроен чат с ID: {chat_id}")


async def on_startup(bot: Bot):
    """Действия при запуске бота"""
    logger.info("Бот запущен")
    
    # Настройка планировщика
    global scheduler
    scheduler = AsyncIOScheduler()
    
    # Добавляем задачу для ежедневной проверки
    hour, minute = map(int, NOTIFICATION_TIME.split(":"))
    scheduler.add_job(
        send_birthday_notifications,
        "cron",
        hour=hour,
        minute=minute,
        args=[bot],
        id="birthday_notifications",
        misfire_grace_time=3600
    )
    
    scheduler.start()
    logger.info(f"Планировщик настроен на {NOTIFICATION_TIME} UTC")


async def on_shutdown(bot: Bot):
    """Действия при остановке бота"""
    logger.info("Бот останавливается")
    if scheduler:
        scheduler.shutdown()


def register_handlers(dp: Dispatcher):
    """Регистрация обработчиков"""
    # Сначала регистрируем обработчики состояний (они должны быть раньше команд!)
    # Состояния для добавления коллеги
    dp.message.register(process_name, StateFilter(AddColleague.waiting_for_name))
    dp.message.register(process_date, StateFilter(AddColleague.waiting_for_date))

    # Состояния для удаления коллеги
    dp.message.register(process_delete_id, StateFilter(DeleteColleague.waiting_for_id))

    # Затем команды
    dp.message.register(start_command, CommandStart())
    dp.message.register(help_command, Command("help"))
    dp.message.register(add_command, Command("add"))
    dp.message.register(list_command, Command("list"))
    dp.message.register(delete_command, Command("delete"))
    dp.message.register(setup_chat_command, Command("setup_chat"))


async def main():
    """Основная функция"""
    global bot
    
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ ОШИБКА: Укажите токен бота в файле config.py")
        print("Получите токен у @BotFather в Telegram")
        return
    
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    
    register_handlers(dp)
    
    # Регистрируем онстартап и оншутдаун
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    # Запуск бота
    logger.info("Запуск бота...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
