"""
Телеграм-бот для приёма заявок
================================
Установка зависимостей:
    pip install python-telegram-bot==20.7

Запуск:
    python bot.py

Замени YOUR_BOT_TOKEN на токен от @BotFather
"""

import logging
from telegram import (
    Update,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# ─── Настройки ────────────────────────────────────────────────────────────────

import os
BOT_TOKEN = os.environ.get("BOT_TOKEN")       # ← вставь сюда новый токен от @BotFather
ADMIN_CHAT_ID = 7964126198         # ← твой Telegram chat_id (уже вставлен)

# ─── Состояния диалога ────────────────────────────────────────────────────────

ASK_NAME, ASK_PHONE, ASK_SERVICE = range(3)

# ─── Логирование ──────────────────────────────────────────────────────────────

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ─── Хендлеры ─────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало диалога — просим имя."""
    await update.message.reply_text(
        "👋 Добро пожаловать!\n\nКак вас зовут?",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ASK_NAME


async def ask_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получили имя — просим телефон."""
    context.user_data["name"] = update.message.text.strip()

    phone_button = KeyboardButton(
        text="📱 Поделиться контактом",
        request_contact=True,
    )
    markup = ReplyKeyboardMarkup(
        [[phone_button]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

    await update.message.reply_text(
        f"Приятно познакомиться, {context.user_data['name']}! 👍\n\n"
        "Пожалуйста, поделитесь номером телефона.",
        reply_markup=markup,
    )
    return ASK_PHONE


async def ask_service(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получили телефон — просим описать услугу."""
    if update.message.contact:
        phone = update.message.contact.phone_number
    else:
        phone = update.message.text.strip()

    context.user_data["phone"] = phone

    await update.message.reply_text(
        "Отлично! Теперь опишите, какая услуга вам нужна.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ASK_SERVICE


async def save_application(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получили услугу — сохраняем и отправляем заявку админу."""
    context.user_data["service"] = update.message.text.strip()

    user = update.effective_user
    data = context.user_data

    # Сообщение для тебя (администратора)
    admin_message = (
        "📋 *Новая заявка!*\n\n"
        f"👤 Имя: {data['name']}\n"
        f"📱 Телефон: {data['phone']}\n"
        f"🛠 Услуга: {data['service']}\n"
        f"🔗 Telegram: @{user.username or '—'} (id: {user.id})"
    )

    try:
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=admin_message,
            parse_mode="Markdown",
        )
        logger.info(f"Заявка отправлена от пользователя {user.id}")
    except Exception as e:
        logger.error(f"Ошибка отправки заявки: {e}")

    # Ответ клиенту
    await update.message.reply_text(
        "✅ Заявка принята! Свяжемся с вами в течение часа.",
        reply_markup=ReplyKeyboardRemove(),
    )

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена диалога."""
    await update.message.reply_text(
        "Диалог отменён. Напишите /start чтобы начать заново.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


# ─── Запуск ───────────────────────────────────────────────────────────────────

def main() -> None:
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_NAME:    [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_phone)],
            ASK_PHONE:   [
                MessageHandler(filters.CONTACT, ask_service),
                MessageHandler(filters.TEXT & ~filters.COMMAND, ask_service),
            ],
            ASK_SERVICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_application)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)

    logger.info("Бот запущен. Нажми Ctrl+C для остановки.")
    app.run_polling()


if __name__ == "__main__":
    main()
