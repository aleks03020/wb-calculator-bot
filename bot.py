import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes

# ---------- НАСТРОЙКИ ----------
BOT_TOKEN = "8830801271:AAE8sPUPBg1SyavYNIDrCOOFG8kimr9K4Fs"

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

# Состояния
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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "🛒 *Калькулятор юнит-экономики Wildberries*\n\n"
        "Считаю чистую прибыль с одной единицы товара.\n"
        "Введи *цену закупки* (сколько платишь поставщику за 1 шт.):",
        parse_mode="Markdown"
    )
    return PURCHASE_PRICE

async def get_purchase_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
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
    try:
        price = float(update.message.text.replace(",", "."))
        if price <= 0:
            raise ValueError
        context.user_data["selling_price"] = price
        
        # Кнопки с категориями
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
    category = update.message.text
    
    if category not in WB_COMMISSION:
        categories = list(WB_COMMISSION.keys())
        keyboard = [[cat] for cat in categories]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text(
            "❌ Выбери категорию из списка:",
            reply_markup=reply_markup
        )
        return CATEGORY
    
    context.user_data["category"] = category
    
    keyboard = [["/skip (по умолчанию 50 ₽)"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text(
        "🚚 Введи *стоимость логистики* за единицу (или нажми кнопку):",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return LOGISTICS

async def get_logistics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        logistics = float(update.message.text.replace(",", "."))
        if logistics < 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Введи число.")
        return LOGISTICS
    
    return await show_result(update, context, logistics)

async def skip_logistics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await show_result(update, context, LOGISTICS_COST)

async def show_result(update: Update, context: ContextTypes.DEFAULT_TYPE, logistics: float):
    result = calculate_profit(
        purchase_price=context.user_data["purchase_price"],
        selling_price=context.user_data["selling_price"],
        category=context.user_data["category"],
        logistics=logistics,
    )
    
    emoji = "✅" if result["net_profit"] > 0 else "❌"
    message = (
        f"📊 *Результат расчёта*\n\n"
        f"  • Цена закупки: {result['purchase_price']} ₽\n"
        f"  • Цена продажи: {result['selling_price']} ₽\n"
        f"  • Комиссия WB ({result['commission_rate']}%): -{result['commission_rub']} ₽\n"
        f"  • Налог УСН (6%): -{result['tax_rub']} ₽\n"
        f"  • Логистика: -{result['logistics']} ₽\n\n"
        f"{emoji} *Чистая прибыль: {result['net_profit']} ₽*\n"
        f"📈 *Маржинальность: {result['margin_percent']}%*"
    )
    
    await update.message.reply_text(message, parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())
    await update.message.reply_text("🔄 Отправь /start для нового расчёта.")
    
    return ConversationHandler.END

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
            LOGISTICS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_logistics),
                CommandHandler("skip", skip_logistics),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    app.add_handler(conv_handler)
    
    print("✅ Бот запущен.")
    app.run_polling()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
