import os
from dotenv import load_dotenv
import logging
import requests
from bs4 import BeautifulSoup
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, CallbackContext
import re

load_dotenv()
token = os.getenv('TELEGRAM_TOKEN')

# Базовый URL для извлечения данных
BASE_URL = 'https://www.exchange-rates.org'

# Установите уровень логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_data(base_url):
    url = f'{base_url}/ru/%D0%B4%D1%80%D0%B0%D0%B3%D0%BC%D0%B5%D1%82%D0%B0%D0%BB%D0%BB%D1%8B/%D1%86%D0%B5%D0%BD%D0%B0-%D0%BD%D0%B0-%D0%B7%D0%BE%D0%BB%D0%BE%D1%82%D0%BE/%D1%83%D0%BA%D1%80%D0%B0%D0%B8%D0%BD%D0%B0/'
    response = requests.get(url)
    response.encoding = 'utf-8'  # Установите правильную кодировку
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Извлекаем строку таблицы с ценой на 24K золото
    price_tag = soup.select_one('#tab_kunit_24 > table > tbody > tr:nth-child(1) > td:nth-child(2)')
    change_tag = soup.select_one('#tab_kunit_24 > table > tbody > tr:nth-child(1) > td.rate.cvc > span.rate-change')
    
    if price_tag and change_tag:
        price_text = price_tag.text.strip()
        change_text = change_tag.text.strip()
        change_class = change_tag.get('class', [])
        
        clean_price_text = re.sub(r'[^\d,]', '', price_text)  # Удалите все нечисловые символы, кроме запятой
        clean_change_text = re.sub(r'[^\d,-]', '', change_text)  # Удалите все нечисловые символы, кроме запятой и минуса
        
        try:
            price = float(clean_price_text.replace(',', '.'))
            change = float(clean_change_text.replace(',', '.'))
            
            # Определяем направление изменения цены по классу элемента
            if 'rate-red' in change_class:
                change_direction = "↓"
            else:
                change_direction = "↑"
                
            return price, round(change, 1), change_direction
        except ValueError:
            return None, None, None
    return None, None, None

def calculate_prices(price_24k):
    karat_to_probe = {
        '24K': 999,
        '22K': 916,
        '18K': 750,
        '14K': 585,
        '10K': 417
    }
    
    prices = {}
    for karat, probe in karat_to_probe.items():
        prices[karat] = round(price_24k * (probe / 999), 2)
    
    return prices

def format_prices_as_table(prices):
    karat_to_probe = {
        '24K': 999,
        '22K': 916,
        '18K': 750,
        '14K': 585,
        '10K': 417
    }
    
    table = "<pre>"
    table += f"{'КАРАТЫ':<10}{'ПРОБА':<10}{'Рыночная цена':<20}\n"
    table += "-"*40 + "\n"
    
    for karat, price in prices.items():
        probe = karat_to_probe[karat]
        table += f"{karat:<10}{probe:<10}{price:<20}\n"
    
    table += "</pre>"
    return table

async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Привет! Отправь мне команду /gold для получения текущей стоимости золота.')

async def get_gold_prices(update: Update, context: CallbackContext) -> None:
    try:
        price_24k, change_24k, change_direction = fetch_data(BASE_URL)
        if price_24k is not None and change_24k is not None:
            prices = calculate_prices(price_24k)
            table = format_prices_as_table(prices)
            message = f'Цена на 24K золото за грамм: {price_24k} (Изменение: {change_direction} на {abs(change_24k)})\n\n'
            message += table
            await update.message.reply_text(message, parse_mode='HTML')
        else:
            await update.message.reply_text('Не удалось получить цену на 24K золото.')
    except Exception as e:
        logger.error("Ошибка при получении цен на золото", exc_info=True)
        await update.message.reply_text('Произошла ошибка при получении данных. Попробуйте позже.')

def main() -> None:
    # Токен вашего бота
    token = '7425752639:AAHvJC5vHudSHU8fhJJuanO4M80qN4L5djM'

    # Создаем Application и передаем ему токен вашего бота.
    application = Application.builder().token(token).build()

    # Регистрация обработчиков команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("gold", get_gold_prices))

    # Запуск бота
    application.run_polling()

if __name__ == '__main__':
    main()
