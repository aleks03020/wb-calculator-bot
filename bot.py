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
            price = float(text)
            user_data[user_id]["purchase"] = price
            user_data[user_id]["step"] = "sell"
            await update.message.reply_text("💰 Введи цену продажи:")

        elif step == "sell":
            price = float(text)
            user_data[user_id]["sell"] = price
            user_data[user_id]["step"] = "category"
            cats = ["Одежда","Обувь","Аксессуары","Бытовая техника","Электроника",
                    "Товары для дома","Спорт","Детские товары","Продукты"]
            keyboard = [[c] for c in cats]
            await update.message.reply_text(
                "📦 Выбери категорию:",
                reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
            )

        elif step == "category":
            commissions = {
                "Одежда": 20, "Обувь": 18, "Аксессуары": 17,
                "Бытовая техника": 12, "Электроника": 12, "Товары для дома": 15,
                "Спорт": 14, "Детские товары": 13, "Продукты": 10,
            }
            if text not in commissions:
                cats = list(commissions.keys())
                keyboard = [[c] for c in cats]
                await update.message.reply_text(
                    "❌ Выбери из списка:",
                    reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
                )
                return
            user_data[user_id]["category"] = text
            user_data[user_id]["step"] = "logistic"
            await update.message.reply_text("🚚 Введи стоимость логистики (или 0):")

        elif step == "logistic":
            logistic = float(text)
            if logistic == 0:
                logistic = 50

            commissions = {
                "Одежда": 20, "Обувь": 18, "Аксессуары": 17,
                "Бытовая техника": 12, "Электроника": 12, "Товары для дома": 15,
                "Спорт": 14, "Детские товары": 13, "Продукты": 10,
            }

            p = user_data[user_id]["purchase"]
            s = user_data[user_id]["sell"]
            cat = user_data[user_id]["category"]
            com = s * commissions[cat] / 100
            tax = s * 6 / 100
            profit = s - p - com - tax - logistic
            margin = (profit / s * 100) if s > 0 else 0

            if user_id not in paid_users:
                user_data[user_id]["count"] = user_data[user_id].get("count", 0) + 1
                remaining = FREE_LIMIT - user_data[user_id]["count"]
                if remaining < 0:
                    remaining = 0
            else:
                remaining = "∞"

            emoji = "✅" if profit > 0 else "❌"
            await update.message.reply_text(
                f"📊 *Результат*\n\n"
                f"Цена закупки: {p} ₽\n"
                f"Цена продажи: {s} ₽\n"
                f"Комиссия WB: -{round(com,2)} ₽\n"
                f"Налог УСН: -{round(tax,2)} ₽\n"
                f"Логистика: -{logistic} ₽\n\n"
                f"{emoji} Прибыль: *{round(profit,2)} ₽*\n"
                f"Маржинальность: *{round(margin,1)}%*\n\n"
                f"Бесплатных расчётов: *{remaining}*",
                parse_mode="Markdown"
            )
            await update.message.reply_text("🔄 /start — новый расчёт")
            user_data[user_id].pop("step", None)

    except ValueError:
        await update.message.reply_text("❌ Введи число:")

async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global ADMIN_ID
    if ADMIN_ID and update.effective_user.id != ADMIN_ID:
        return
    try:
        target_id = int(context.args[0])
        paid_users.add(target_id)
        user_data.pop(target_id, None)
        await update.message.reply_text(f"✅ Доступ открыт для `{target_id}`", parse_mode="Markdown")
        try:
            await context.bot.send_message(chat_id=target_id, text="✅ Доступ открыт! Отправь /start")
        except:
            pass
    except:
        await update.message.reply_text("❌ Формат: /approve ID_пользователя")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("approve", approve))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ Бот запущен.")
    app.run_polling()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
