import os
import subprocess
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.utils import executor

API_TOKEN = '7471696949:AAGP6xmotd0RPRhgI2j1x_0AaZHHUmQlbEI'
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

async def download_magnet(magnet_link):
    download_path = "/path/to/download"
    os.makedirs(download_path, exist_ok=True)
    download_command = ["aria2c", "-d", download_path, magnet_link]
    subprocess.run(download_command)
    files = os.listdir(download_path)
    if files:
        file_path = os.path.join(download_path, files[0])
        return file_path
    return None

async def upload_to_wormhole(file_path):
    with open(file_path, 'rb') as f:
        response = requests.post('https://wormhole.app/upload', files={'file': f})
    if response.status_code == 200:
        return response.json().get('url')
    return None

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.reply("Привет! Отправьте мне magnet ссылку, и я загружу файл на wormhole.app.")

@dp.message_handler()
async def handle_message(message: types.Message):
    magnet_link = message.text
    await message.reply("Скачиваю файл...")
    file_path = await download_magnet(magnet_link)
    if file_path:
        await message.reply("Загружаю файл на wormhole.app...")
        url = await upload_to_wormhole(file_path)
        if url:
            await message.reply(f"Файл загружен: {url}")
        else:
            await message.reply("Ошибка загрузки файла на wormhole.app.")
        os.remove(file_path)
    else:
        await message.reply("Ошибка скачивания файла.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)