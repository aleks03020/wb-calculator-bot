import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = "8863928670:AAEYlf9rQNT2J-PWwhdSFPdag0ez5SvyLqI"

WB_COMMISSION = {
    "Одежда": 20, "Обувь": 18, "Аксессуары": 17,
    "Бытовая техника": 12, "Электроника": 12, "Товары для дома": 15,
    "Спорт": 14, "Детские товары": 13, "Продукты": 10,
}

# Временное хранилище данных пользователя
user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data[update.effective_user.id] = {"step": "price"}
    await update.message.reply_text("🛒 Введи цену закупки (за 1 шт.):")
    print(f"START: user {update.effective_user.id}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.replace(",", ".")
    print(f"MSG from {user_id}: {text}")

    if user_id not in user_data:
        await start(update, context)
        return

    step = user_data[user_id].get("step", "price")

    try:
        # Шаг 1: цена закупки
        if step == "price":
            price = float(text)
            user_data[user_id]["purchase"] = price
            user_data[user_id]["step"] = "sell"
            await update.message.reply_text("💰 Введи цену продажи:")

        # Шаг 2: цена продажи
        elif step == "sell":
            price = float(text)
            user_data[user_id]["sell"] = price
            user_data[user_id]["step"] = "category"
            cats = list(WB_COMMISSION.keys())
            keyboard = [[c] for c in cats]
            await update.message.reply_text(
                "📦 Выбери категорию:",
                reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
            )

        # Шаг 3: категория
        elif step == "category":
            if text not in WB_COMMISSION:
                cats = list(WB_COMMISSION.keys())
                keyboard = [[c] for c in cats]
                await update.message.reply_text(
                    "❌ Выбери из списка:",
                    reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
                )
                return
            user_data[user_id]["category"] = text
            user_data[user_id]["step"] = "logistic"
            await update.message.reply_text("🚚 Введи стоимость логистики (или 0):")

        # Шаг 4: логистика и результат
        elif step == "logistic":
            logistic = float(text)
            if logistic == 0:
                logistic = 50

            p = user_data[user_id]["purchase"]
            s = user_data[user_id]["sell"]
            cat = user_data[user_id]["category"]
            com = s * WB_COMMISSION[cat] / 100
            tax = s * 6 / 100
            profit = s - p - com - tax - logistic
            margin = (profit / s * 100) if s > 0 else 0

            emoji = "✅" if profit > 0 else "❌"
            await update.message.reply_text(
                f"📊 *Результат*\n\n"
                f"Цена закупки: {p} ₽\n"
                f"Цена продажи: {s} ₽\n"
                f"Комиссия WB: -{round(com,2)} ₽\n"
                f"Налог УСН: -{round(tax,2)} ₽\n"
                f"Логистика: -{logistic} ₽\n\n"
                f"{emoji} Прибыль: *{round(profit,2)} ₽*\n"
                f"Маржинальность: *{round(margin,1)}%*",
                parse_mode="Markdown"
            )
            await update.message.reply_text("🔄 /start — новый расчёт")
            user_data.pop(user_id, None)

    except ValueError:
        await update.message.reply_text("❌ Введи число. Попробуй ещё раз:")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data.pop(update.effective_user.id, None)
    await update.message.reply_text("👋 Отменено. /start для начала.")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ Бот запущен.")
    app.run_polling()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
