 logging
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

async def get_purchase_price
