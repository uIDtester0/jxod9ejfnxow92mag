import asyncio
import os
import shutil
import time
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import libtorrent as lt

# Замените 'YOUR_BOT_TOKEN_HERE' на ваш токен от BotFather
TOKEN = '7471696949:AAGP6xmotd0RPRhgI2j1x_0AaZHHUmQlbEI'
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Создаем глобальную сессию libtorrent
session = lt.session()

# Словарь для отслеживания загрузок пользователей
downloads = {}

# Обработчик команды /start
async def start_cmd(message: types.Message):
    await message.answer("Добро пожаловать в Magnet Downloader Bot! Отправьте мне magnet-ссылку для начала загрузки.")

# Обработчик команды /help
async def help_cmd(message: types.Message):
    await message.answer("Команды:\n/start - Запустить бота\n/help - Показать помощь\n/status - Проверить статус загрузки\n/cancel - Отменить текущую загрузку")

# Обработчик magnet-ссылок
async def handle_magnet(message: types.Message):
    user_id = message.from_user.id
    # Проверяем, есть ли уже активная загрузка у пользователя
    if user_id in downloads and downloads[user_id]['task'] is not None:
        await message.answer("У вас уже есть активная загрузка. Дождитесь её завершения или отмените её.")
        return

    # Создаем уникальную папку для загрузки
    save_path = f'./downloads/{user_id}_{int(time.time())}'
    os.makedirs(save_path, exist_ok=True)

    # Параметры для добавления торрента
    params = {'save_path': save_path, 'url': message.text}
    handle = session.add_torrent(params)

    # Сохраняем информацию о загрузке
    downloads[user_id] = {'handle': handle, 'task': None, 'file_path': None}

    # Запускаем асинхронную задачу для загрузки
    task = asyncio.create_task(download_loop(user_id, save_path))
    downloads[user_id]['task'] = task

    await message.answer("Загрузка началась.")

# Асинхронная функция для управления процессом загрузки
async def download_loop(user_id, save_path):
    handle = downloads[user_id]['handle']
    try:
        # Ждем получения метаданных торрента
        while not handle.has_metadata():
            await asyncio.sleep(1)

        # Получаем информацию о торренте
        ti = handle.get_torrent_info()
        files = ti.files()

        # Проверяем, что торрент содержит только один файл
        if len(files) > 1:
            await bot.send_message(user_id, "Этот торрент содержит несколько файлов, но я поддерживаю только одиночные файлы.")
            session.remove_torrent(handle)
            shutil.rmtree(save_path)
            del downloads[user_id]
            return

        # Путь к файлу
        file_path = os.path.join(save_path, files[0].path)
        downloads[user_id]['file_path'] = file_path

        # Ждем завершения загрузки
        while True:
            status = handle.status()
            if status.state == lt.torrent_status.seeding:  # Загрузка завершена
                break
            await asyncio.sleep(5)

        # Проверяем размер файла и отправляем, если он меньше 50 МБ
        file_size = os.path.getsize(file_path)
        if file_size > 50 * 1024 * 1024:
            await bot.send_message(user_id, "Файл слишком большой для отправки (>50 МБ).")
        else:
            with open(file_path, 'rb') as f:
                await bot.send_document(user_id, f)

        # Очищаем после завершения
        session.remove_torrent(handle)
        shutil.rmtree(save_path)
        del downloads[user_id]

    except asyncio.CancelledError:
        # Обработка отмены загрузки
        handle.pause()
        session.remove_torrent(handle)
        shutil.rmtree(save_path)
        del downloads[user_id]
        await bot.send_message(user_id, "Загрузка отменена.")

    except Exception as e:
        # Обработка ошибок (например, неверная ссылка или нет сидеров)
        await bot.send_message(user_id, f"Произошла ошибка: {e}")
        session.remove_torrent(handle)
        shutil.rmtree(save_path)
        del downloads[user_id]

# Обработчик команды /status
async def status_cmd(message: types.Message):
    user_id = message.from_user.id
    if user_id in downloads and downloads[user_id]['handle'] is not None:
        status = downloads[user_id]['handle'].status()
        progress = status.progress * 100
        await message.answer(f"Прогресс загрузки: {progress:.2f}%")
    else:
        await message.answer("Нет активной загрузки.")

# Обработчик команды /cancel
async def cancel_cmd(message: types.Message):
    user_id = message.from_user.id
    if user_id in downloads and downloads[user_id]['task'] is not None:
        downloads[user_id]['task'].cancel()
        await message.answer("Отмена загрузки...")
    else:
        await message.answer("Нет активной загрузки для отмены.")

# Регистрация обработчиков
dp.message.register(start_cmd, Command('start'))
dp.message.register(help_cmd, Command('help'))
dp.message.register(status_cmd, Command('status'))
dp.message.register(cancel_cmd, Command('cancel'))
dp.message.register(handle_magnet, lambda message: message.text.startswith('magnet:?'))

# Запуск бота
async def main():
    os.makedirs('./downloads', exist_ok=True)  # Создаем папку для загрузок
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())