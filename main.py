import os
import asyncio
import libtorrent as lt
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

# Конфигурация
API_TOKEN = "7471696949:AAGP6xmotd0RPRhgI2j1x_0AaZHHUmQlbEI"
DOWNLOADS_DIR = "downloads"
WORMHOLE_API = "https://wormhole.app/api/v1"

# Инициализация бота
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Скачивание торрента по magnet-ссылке
async def download_torrent(magnet_link: str):
    ses = lt.session()
    params = {
        "save_path": DOWNLOADS_DIR,
        "storage_mode": lt.storage_mode_t.storage_mode_sparse,
    }
    
    handle = lt.add_magnet_uri(ses, magnet_link, params)
    ses.start_dht()

    # Ожидание метаданных
    while not handle.has_metadata():
        await asyncio.sleep(1)
    
    # Скачивание файла
    while handle.status().state != lt.torrent_status.seeding:
        status = handle.status()
        print(f"Прогресс: {status.progress * 100:.1f}%")
        await asyncio.sleep(5)
    
    return os.path.join(DOWNLOADS_DIR, handle.name())

# Загрузка на Wormhole.app
def upload_to_wormhole(file_path: str):
    try:
        # Создание "червяка" (временного хранилища)
        response = requests.post(
            f"{WORMHOLE_API}/worms",
            json={"ttl": 86400}  # Время жизни файла: 24 часа
        )
        worm_id = response.json()["id"]

        # Загрузка файла
        with open(file_path, "rb") as f:
            requests.put(
                f"{WORMHOLE_API}/worms/{worm_id}/file",
                files={"file": f}
            )

        return f"https://wormhole.app/{worm_id}#"

    except Exception as e:
        raise Exception(f"Ошибка загрузки: {str(e)}")

# Обработчики сообщений
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.answer("Отправьте magnet-ссылку для скачивания файла.")

@dp.message_handler(lambda msg: msg.text.startswith("magnet:"))
async def process_magnet(message: types.Message):
    try:
        # Скачивание файла
        await message.answer("⏳ Начинаю скачивание...")
        file_path = await download_torrent(message.text)

        # Загрузка на Wormhole
        await message.answer("🚀 Загружаю файл на Wormhole.app...")
        download_url = upload_to_wormhole(file_path)

        # Отправка ссылки
        await message.answer(f"✅ Файл готов! Ссылка для скачивания:\n{download_url}")

        # Удаление локального файла
        os.remove(file_path)

    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")
        if "file_path" in locals():
            os.remove(file_path)

if __name__ == "__main__":
    # Создание папки для загрузок
    if not os.path.exists(DOWNLOADS_DIR):
        os.makedirs(DOWNLOADS_DIR)
    
    executor.start_polling(dp, skip_updates=True)