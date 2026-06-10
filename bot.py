import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ЗАМЕНИ НА СВОИ ДАННЫЕ:
BOT_TOKEN = "8863928670:AAEYlf9rQNT2J-PWwhdSFPdag0ez5SvyLqI"
CARD_NUMBER = "2202 2050 1088 5801"

FREE_LIMIT = 5
PRICE = 299
ADMIN_ID = None

user_data = {}
paid_users = set()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global ADMIN_ID
    user_id = update.effective_user.id
    if ADMIN_ID is None:
        ADMIN_ID = user_id

    # Проверка лимита
    if user_id not in paid_users:
        if user_id not in user_data:
            user_data[user_id] = {"count": 0}
        if user_data[user_id]["count"] >= FREE_LIMIT:
            await update.message.reply_text(
                f"⚠️ *Лимит исчерпан!*\n\n"
                f"Вы использовали {FREE_LIMIT} расчётов.\n"
                f"Переведите {PRICE}₽ на карту:\n`{CARD_NUMBER}`\n\n"
                f"Затем напишите: *Оплатил*",
                parse_mode="Markdown"
            )
            return

    user_data[user_id] = user_data.get(user_id, {"count": 0})
    user_data[user_id]["step"] = "price"
    await update.message.reply_text("🛒 Введи цену закупки (за 1 шт.):")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    # Проверка на "Оплатил"
    if text.lower() == "оплатил":
        user = update.effective_user
        name = f"@{user.username}" if user.username else user.full_name
        if ADMIN_ID:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"🔔 *Новый платёж!*\n\nКто: {name}\nID: `{user_id}`\n\nПодтверди: `/approve {user_id}`",
                parse_mode="Markdown"
            )
        await update.message.reply_text("✅ Админ уже проверяет. Доступ откроют вручную.")
        return

    text = text.replace(",", ".")

    if user_id not in user_data:
        await start(update, context)
        return

    step = user_data[user_id].get("step", "price")

    try:
        if step == "price":
            
