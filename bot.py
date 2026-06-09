import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes

# ---------- НАСТРОЙКИ ----------
BOT_TOKEN = "8830801271:AAE8sPUPBg1SyavYNIDrCOOFG8kimr9K4Fs"

# Твой номер ЮMoney (замени на свой)
YOMONEY_WALLET = "4100119540352192"

# Твой Telegram ID (для уведомлений об оплате)
ADMIN_ID = None  # Пока не знаем — бот сам определит

WB_COMMISSION = {
    "Одежда": 20,
    "Обувь": 18,
    "Аксессуары": 17,
    "Бытовая техника": 12,
    "Электроника": 12,
    "Товары для дома": 15,
    "Спорт": 14,
    "Детские товары": 13,
    "Продукты": 10,
}

TAX_RATE = 6
LOGISTICS_COST = 50
FREE_LIMIT = 5  # Бесплатных расчётов
SUBSCRIPTION_PRICE = 299  # Цена подписки

# Хранилище пользователей (словарь)
users = {}

PURCHASE_PRICE, SELLING_PRICE, CATEGORY, LOGISTICS = range(4)

def calculate_profit(purchase_price, selling_price, category, logistics=LOGISTICS_COST):
    commission_rate = WB_COMMISSION.get(category, 18)
    commission_rub = selling_price * commission_rate / 100
    tax_rub = selling_price * TAX_RATE / 100
    net_profit = selling_price - purchase_price - commission_rub - tax_rub - logistics
    margin_percent = (net_profit / selling_price * 100) if selling_price > 0 else 0
    
    return {
        "purchase_price": purchase_price,
        "selling_price": selling_price,
        "commission_rate": commission_rate,
        "commission_rub": round(commission_rub, 2),
        "tax_rub": round(tax_rub, 2),
        "logistics": logistics,
        "net_profit": round(net_profit, 2),
        "margin_percent": round(margin_percent, 1),
    }

def check_limit(user_id):
    """Проверяет, не исчерпан ли лимит. True — можно считать дальше."""
    if user_id not in users:
        users[user_id] = {"count": 0, "paid": False}
    
    if users[user_id]["paid"]:
        return True
    
    if users[user_id]["count"] < FREE_LIMIT:
        return True
    
    return False

def increment_count(user_id):
    """Увеличивает счётчик расчётов."""
    if user_id not in users:
        users[user_id] = {"count": 0, "paid": False}
    users[user_id]["count"] += 1

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    
    # Определяем админа (первый, кто написал боту)
    global ADMIN_ID
    if ADMIN_ID is None:
        ADMIN_ID = user_id
    
    if not check_limit(user_id):
        await update.message.reply_text(
            f"⚠️ *Лимит исчерпан!*\n\n"
            f"Вы использовали {FREE_LIMIT} бесплатных расчётов.\n"
            f"Чтобы продолжить, переведите *{SUBSCRIPTION_PRICE}₽* на ЮMoney:\n"
            f"`{YOMONEY_WALLET}`\n\n"
            f"После оплаты напишите сюда же: *Оплатил*",
            parse_mode="Markdown"
        )
        return ConversationHandler.END
    
    await update.message.reply_text(
        "🛒 *Калькулятор юнит-экономики Wildberries*\n\n"
        "Считаю чистую прибыль с одной единицы товара.\n"
        "Введи *цену закупки* (сколько платишь поставщику за 1 шт.):",
        parse_mode="Markdown"
    )
    return PURCHASE_PRICE

async def get_purchase_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    
    if not check_limit(user_id):
        await update.message.reply_text(
            f"⚠️ Лимит исчерпан! Переведите {SUBSCRIPTION_PRICE}₽ на {YOMONEY_WALLET} и напишите «Оплатил»."
        )
        return ConversationHandler.END
    
    try:
        price = float(update.message.text.replace(",", "."))
        if price <= 0:
            raise ValueError
        context.user_data["purchase_price"] = price
        await update.message.reply_text("💰 Введи *цену продажи* на Wildberries:", parse_mode="Markdown")
        return SELLING_PRICE
    except ValueError:
        await update.message.reply_text("❌ Введи число (например: 500 или 499.90).")
        return PURCHASE_PRICE

async def get_selling_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    
    if not check_limit(user_id):
        await update.message.reply_text(
            f"⚠️ Лимит исчерпан! Переведите {SUBSCRIPTION_PRICE}₽ на {YOMONEY_WALLET} и напишите «Оплатил»."
        )
        return ConversationHandler.END
    
    try:
        price = float(update.message.text.replace(",", "."))
        if price <= 0:
            raise ValueError
        context.user_data["selling_price"] = price
        
        categories = list(WB_COMMISSION.keys())
        keyboard = [[cat] for cat in categories]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        await update.message.reply_text(
            "📦 Выбери *категорию товара*:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return CATEGORY
    except ValueError:
        await update.message.reply_text("❌ Введи число.")
        return SELLING_PRICE

async def get_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    
    if not check_limit(user_id):
        await update.message.reply_text(
            f"⚠️ Лимит исчерпан! Переведите {SUBSCRIPTION_PRICE}₽ на {YOMONEY_WALLET} и напишите «Оплатил»."
        )
        return ConversationHandler.END
    
    category = update.message.text
    
    if category not in WB_COMMISSION:
        categories = list(WB_COMMISSION.keys())
        keyboard = [[cat] for cat in categories]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text("❌ Выбери категорию из списка:", reply_markup=reply_markup)
        return CATEGORY
    
    context.user_data["category"] = category
    
    await update.message.reply_text(
        "🚚 Введи *стоимость логистики* за единицу (или отправь 0, если не знаешь):",
        parse_mode="Markdown"
    )
    return LOGISTICS

async def get_logistics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    
    if not check_limit(user_id):
        await update.message.reply_text(
            f"⚠️ Лимит исчерпан! Переведите {SUBSCRIPTION_PRICE}₽ на {YOMONEY_WALLET} и напишите «Оплатил»."
        )
        return ConversationHandler.END
    
    try:
        logistics = float(update.message.text.replace(",", "."))
        if logistics < 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Введи число.")
        return LOGISTICS
    
    if logistics == 0:
        logistics = LOGISTICS_COST
    
    increment_count(user_id)
    
    result = calculate_profit(
        purchase_price=context.user_data["purchase_price"],
        selling_price=context.user_data["selling_price"],
        category=context.user_data["category"],
        logistics=logistics,
    )
    
    emoji = "✅" if result["net_profit"] > 0 else "❌"
    
    # Считаем оставшиеся расчёты
    remaining = FREE_LIMIT - users[user_id]["count"]
    if remaining < 0:
        remaining = 0
    
    message = (
        f"📊 *Результат расчёта*\n\n"
        f"  • Цена закупки: {result['purchase_price']} ₽\n"
        f"  • Цена продажи: {result['selling_price']} ₽\n"
        f"  • Комиссия WB ({result['commission_rate']}%): -{result['commission_rub']} ₽\n"
        f"  • Налог УСН (6%): -{result['tax_rub']} ₽\n"
        f"  • Логистика: -{result['logistics']} ₽\n\n"
        f"{emoji} *Чистая прибыль: {result['net_profit']} ₽*\n"
        f"📈 *Маржинальность: {result['margin_percent']}%*\n\n"
        f"🆓 Осталось бесплатных расчётов: *{remaining}*"
    )
    
    await update.message.reply_text(message, parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())
    
    if remaining == 0:
        await update.message.reply_text(
            f"⚠️ Это был последний бесплатный расчёт!\n"
            f"Для продолжения — {SUBSCRIPTION_PRICE}₽ на `{YOMONEY_WALLET}`\n"
            f"После оплаты напишите: *Оплатил*",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("🔄 Отправь /start для нового расчёта.")
    
    return ConversationHandler.END

async def handle_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает сообщение 'Оплатил'"""
    user_id = update.effective_user.id
    text = update.message.text.lower()
    
    if text == "оплатил":
        # Уведомляем админа
        user = update.effective_user
        user_info = f"@{user.username}" if user.username else user.full_name
        
        if ADMIN_ID:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"🔔 *Новая оплата!*\n\nПользователь: {user_info}\nID: `{user_id}`\n\nПроверь перевод и отправь команду:\n`/approve {user_id}`",
                parse_mode="Markdown"
            )
        
        await update.message.reply_text("✅ Я сообщил администратору. Как только он проверит платёж, доступ откроется. Обычно это занимает пару минут.")
        return
    
    # Если написал что-то другое — игнорируем
    return

async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Админ подтверждает оплату: /approve 123456"""
    user_id = update.effective_user.id
    
    # Проверяем, что это админ
    if ADMIN_ID and user_id != ADMIN_ID:
        await update.message.reply_text("❌ У вас нет прав.")
        return
    
    # Получаем ID пользователя из команды
    try:
        target_id = int(context.args[0])
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Используй: /approve ID_пользователя")
        return
    
    # Открываем доступ
    if target_id not in users:
        users[target_id] = {"count": 0, "paid": False}
    
    users[target_id]["paid"] = True
    users[target_id]["count"] = 0  # Сбрасываем счётчик
    
    await update.message.reply_text(f"✅ Доступ открыт для пользователя `{target_id}`!", parse_mode="Markdown")
    
    # Уведомляем пользователя
    try:
        await context.bot.send_message(
            chat_id=target_id,
            text="✅ *Оплата получена!* Доступ открыт навсегда. Отправьте /start для расчёта.",
            parse_mode="Markdown"
        )
    except:
        await update.message.reply_text("⚠️ Не смог уведомить пользователя.")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("👋 Отменено. /start для нового расчёта.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            PURCHASE_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_purchase_price)],
            SELLING_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_selling_price)],
            CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_category)],
            LOGISTICS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_logistics)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("approve", approve))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_payment))
    
    print("✅ Бот запущен.")
    app.run_polling()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
