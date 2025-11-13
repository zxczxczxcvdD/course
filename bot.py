import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен бота
BOT_TOKEN = "8531526598:AAHJsvX-2H5C_YzbgxMXWYREbx59TCfuNhM"

# Список криптовалют для отслеживания
CRYPTO_CURRENCIES = {
    'the-open-network': {'name': 'TON', 'symbol': 'TON', 'emoji': '💎', 'alternative_source': 'tonapi'},
    'bitcoin': {'name': 'Bitcoin', 'symbol': 'BTC', 'emoji': '₿'},
    'ethereum': {'name': 'Ethereum', 'symbol': 'ETH', 'emoji': 'Ξ'},
}

# Функция для получения курса TON через TonAPI
def get_ton_price_tonapi() -> dict:
    """Получает курс TON через TonAPI"""
    try:
        url = "https://tonapi.io/v2/rates"
        params = {
            'tokens': 'ton',
            'currencies': 'usd,rub,uah'
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if 'rates' in data and 'TON' in data['rates']:
            ton_data = data['rates']['TON']
            usd_price = ton_data.get('USD')
            rub_price = ton_data.get('RUB')
            uah_price = ton_data.get('UAH')

            if usd_price is not None or rub_price is not None or uah_price is not None:
                # Пытаемся получить дополнительные данные через CoinGecko
                try:
                    coingecko_data = get_crypto_price_coingecko('the-open-network')
                except Exception:
                    coingecko_data = None

                result = {
                    'usd': usd_price,
                    'rub': rub_price,
                    'uah': uah_price,
                    'usd_24h_change': coingecko_data.get('usd_24h_change', 0) if coingecko_data else 0,
                    'rub_24h_change': coingecko_data.get('rub_24h_change', 0) if coingecko_data else 0,
                    'uah_24h_change': coingecko_data.get('uah_24h_change', 0) if coingecko_data else 0,
                    'usd_24h_vol': coingecko_data.get('usd_24h_vol', 0) if coingecko_data else 0,
                    'usd_market_cap': coingecko_data.get('usd_market_cap', 0) if coingecko_data else 0
                }

                # Если CoinGecko недоступен, заменяем None значениями по умолчанию
                if result['usd'] is None and coingecko_data:
                    result['usd'] = coingecko_data.get('usd')
                if result['rub'] is None and coingecko_data:
                    result['rub'] = coingecko_data.get('rub')
                if result['uah'] is None and coingecko_data:
                    result['uah'] = coingecko_data.get('uah')

                return result
        return None
    except Exception as e:
        logger.error(f"Ошибка при получении курса TON через TonAPI: {e}")
        return None

# Функция для получения курса криптовалюты через CoinGecko
def get_crypto_price_coingecko(crypto_id: str) -> dict:
    """Получает текущий курс криптовалюты с CoinGecko API"""
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            'ids': crypto_id,
            'vs_currencies': 'usd,rub,uah',
            'include_24hr_change': 'true',
            'include_24hr_vol': 'true',
            'include_market_cap': 'true'
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if crypto_id in data:
            return data[crypto_id]
        return None
    except Exception as e:
        logger.error(f"Ошибка при получении курса {crypto_id} через CoinGecko: {e}")
        return None

# Основная функция для получения курса криптовалюты
def get_crypto_price(crypto_id: str) -> dict:
    """Получает текущий курс криптовалюты с использованием основного и альтернативных источников"""
    crypto_info = CRYPTO_CURRENCIES.get(crypto_id)
    
    # Если есть альтернативный источник, пробуем его сначала
    if crypto_info and 'alternative_source' in crypto_info:
        if crypto_info['alternative_source'] == 'tonapi':
            ton_data = get_ton_price_tonapi()
            if ton_data:
                return ton_data
    
    # Пробуем CoinGecko
    coingecko_data = get_crypto_price_coingecko(crypto_id)
    if coingecko_data:
        return coingecko_data
    
    # Если CoinGecko не сработал, но есть альтернативный источник, пробуем его
    if crypto_info and 'alternative_source' in crypto_info:
        if crypto_info['alternative_source'] == 'tonapi':
            ton_data = get_ton_price_tonapi()
            if ton_data:
                return ton_data
    
    return None

# Функция для форматирования цены
def format_price(price: float) -> str:
    """Форматирует цену для красивого отображения"""
    if price >= 1:
        return f"${price:,.2f}"
    elif price >= 0.01:
        return f"${price:.4f}"
    else:
        return f"${price:.8f}"

# Функция для форматирования цены в рублях
def format_price_rub(price: float) -> str:
    """Форматирует цену в рублях"""
    if price >= 1:
        return f"₽{price:,.2f}"
    elif price >= 0.01:
        return f"₽{price:.4f}"
    else:
        return f"₽{price:.8f}"

# Функция для форматирования цены в гривнах
def format_price_uah(price: float) -> str:
    """Форматирует цену в гривнах"""
    if price >= 1:
        return f"₴{price:,.2f}"
    elif price >= 0.01:
        return f"₴{price:.4f}"
    else:
        return f"₴{price:.8f}"

# Функция для форматирования больших чисел
def format_large_number(num: float) -> str:
    """Форматирует большие числа (объем, капитализация)"""
    if num >= 1_000_000_000_000:
        return f"${num/1_000_000_000_000:.2f}T"
    elif num >= 1_000_000_000:
        return f"${num/1_000_000_000:.2f}B"
    elif num >= 1_000_000:
        return f"${num/1_000_000:.2f}M"
    else:
        return f"${num:,.0f}"

# Функция для форматирования изменения цены
def format_change(change: float) -> str:
    """Форматирует изменение цены с эмодзи"""
    if change > 0:
        return f"📈 +{change:.2f}%"
    elif change < 0:
        return f"📉 {change:.2f}%"
    else:
        return f"➡️ {change:.2f}%"

# Функция для создания клавиатуры с кнопками криптовалют
def create_crypto_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру с кнопками выбора криптовалют"""
    buttons = []
    row = []
    
    for i, (crypto_id, crypto_info) in enumerate(CRYPTO_CURRENCIES.items()):
        button = InlineKeyboardButton(
            text=f"{crypto_info['emoji']} {crypto_info['symbol']}",
            callback_data=f"crypto_{crypto_id}"
        )
        row.append(button)
        
        # Размещаем по 3 кнопки в ряду
        if len(row) == 3 or i == len(CRYPTO_CURRENCIES) - 1:
            buttons.append(row)
            row = []
    
    buttons.append([InlineKeyboardButton("🔄 Обновить", callback_data="refresh")])
    
    return InlineKeyboardMarkup(buttons)

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    user = update.effective_user
    welcome_message = f"""
👋 Привет, {user.first_name}!

💰 Я бот для отслеживания курсов криптовалют!

📊 Доступные функции:
• Выберите криптовалюту из списка для просмотра детальной информации
• Просмотр всех курсов одновременно
• Автоматическое обновление данных

🎯 Выберите криптовалюту из меню ниже:
"""
    keyboard = create_crypto_keyboard()
    await update.message.reply_text(
        welcome_message,
        reply_markup=keyboard,
        parse_mode='HTML'
    )

# Обработчик команды /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /help"""
    help_text = """
📖 <b>Справка по использованию бота</b>

<b>Команды:</b>
/start - Начать работу с ботом
/help - Показать эту справку
/crypto - Показать меню выбора криптовалют

<b>Функции:</b>
• Нажмите на кнопку с криптовалютой для просмотра детальной информации
• Используйте кнопку "📊 Все курсы" для просмотра всех курсов
• Кнопка "🔄 Обновить" обновит данные

<b>Отслеживаемые криптовалюты:</b>
"""
    for crypto_info in CRYPTO_CURRENCIES.values():
        help_text += f"• {crypto_info['emoji']} {crypto_info['name']} ({crypto_info['symbol']})\n"
    
    keyboard = create_crypto_keyboard()
    await update.message.reply_text(
        help_text,
        reply_markup=keyboard,
        parse_mode='HTML'
    )

# Обработчик команды /crypto
async def crypto_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /crypto"""
    message = "💰 <b>Выберите криптовалюту для просмотра курса:</b>"
    keyboard = create_crypto_keyboard()
    await update.message.reply_text(
        message,
        reply_markup=keyboard,
        parse_mode='HTML'
    )

# Обработчик нажатий на кнопки
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик нажатий на inline кнопки"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "refresh":
        # Обновляем меню
        message = "💰 <b>Выберите криптовалюту для просмотра курса:</b>"
        keyboard = create_crypto_keyboard()
        await query.edit_message_text(
            message,
            reply_markup=keyboard,
            parse_mode='HTML'
        )
    
    elif query.data.startswith("crypto_"):
        # Показываем детальную информацию о криптовалюте
        crypto_id = query.data.replace("crypto_", "")
        crypto_info = CRYPTO_CURRENCIES.get(crypto_id)
        
        if not crypto_info:
            await query.edit_message_text("❌ Криптовалюта не найдена")
            return
        
        price_data = get_crypto_price(crypto_id)
        
        if price_data:
            price_usd = price_data.get('usd')
            price_rub = price_data.get('rub')
            price_uah = price_data.get('uah')
            change_usd = price_data.get('usd_24h_change')
            change_rub = price_data.get('rub_24h_change')
            change_uah = price_data.get('uah_24h_change')
            volume_24h = price_data.get('usd_24h_vol', 0)
            market_cap = price_data.get('usd_market_cap', 0)

            price_lines = []
            if price_usd is not None:
                price_lines.append(f"💵 <b>Цена (USD):</b> {format_price(price_usd)}")
            if price_rub is not None:
                price_lines.append(f"🇷🇺 <b>Цена (RUB):</b> {format_price_rub(price_rub)}")
            if price_uah is not None:
                price_lines.append(f"🇺🇦 <b>Цена (UAH):</b> {format_price_uah(price_uah)}")

            change_lines = []
            if change_usd is not None:
                change_lines.append(f"• USD {format_change(change_usd)}")
            if change_rub is not None:
                change_lines.append(f"• RUB {format_change(change_rub)}")
            if change_uah is not None:
                change_lines.append(f"• UAH {format_change(change_uah)}")

            change_block = "\n".join(change_lines) if change_lines else "• Данные недоступны"
            price_block = "\n".join(price_lines) if price_lines else "💵 Данные о цене недоступны"

            message = f"""
{crypto_info['emoji']} <b>{crypto_info['name']}</b> ({crypto_info['symbol']})

{price_block}

📈 <b>Изменение за 24 часа:</b>
{change_block}

📊 <b>Статистика за 24 часа (USD):</b>
• Объем торгов: {format_large_number(volume_24h)}
• Рыночная капитализация: {format_large_number(market_cap)}
"""
        else:
            message = f"""
{crypto_info['emoji']} <b>{crypto_info['name']}</b> ({crypto_info['symbol']})

⚠️ Не удалось получить данные о курсе.
Попробуйте позже.
"""
        
        keyboard = create_crypto_keyboard()
        await query.edit_message_text(
            message,
            reply_markup=keyboard,
            parse_mode='HTML'
        )

def main() -> None:
    """Запуск бота"""
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("crypto", crypto_menu))
    
    # Регистрируем обработчик кнопок
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Запускаем бота
    logger.info("Бот запущен...")
    application.run_polling()

if __name__ == '__main__':
    main()

