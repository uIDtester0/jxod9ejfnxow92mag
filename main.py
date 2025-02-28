import os
import asyncio
import tempfile
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

API_TOKEN = '7471696949:AAGP6xmotd0RPRhgI2j1x_0AaZHHUmQlbEI'
WORMHOLE_TIMEOUT = 60 * 60  # 1 hour timeout for wormhole

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

async def download_torrent(magnet_link, download_dir):
    command = [
        'aria2c',
        '--dir=' + download_dir,
        '--seed-time=0',
        '--enable-dht=false',
        '--disable-ipv6=true',
        '--quiet=true',
        magnet_link
    ]
    
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    await process.wait()
    return process.returncode == 0

async def send_via_wormhole(file_path):
    command = [
        'wormhole',
        'send',
        '--hide-progress',
        '--code-length=2',
        file_path
    ]
    
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=WORMHOLE_TIMEOUT)
    except asyncio.TimeoutError:
        process.kill()
        return None
    
    if process.returncode != 0:
        return None
    
    return stdout.decode().strip()

async def process_magnet(magnet_link):
    with tempfile.TemporaryDirectory() as temp_dir:
        success = await download_torrent(magnet_link, temp_dir)
        if not success:
            return None
        
        files = [f for f in os.listdir(temp_dir) if os.path.isfile(os.path.join(temp_dir, f))]
        if not files:
            return None
        
        largest_file = max(files, key=lambda f: os.path.getsize(os.path.join(temp_dir, f)))
        file_path = os.path.join(temp_dir, largest_file)
        
        return await send_via_wormhole(file_path)

@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    await message.reply("Отправьте мне magnet-ссылку, и я перешлю вам файл через Wormhole!")

@dp.message_handler(regexp=r'^magnet:\?xt=urn:btih:[a-zA-Z0-9]+.*')
async def handle_magnet(message: types.Message):
    msg = await message.reply("⏳ Обрабатываю magnet-ссылку...")
    magnet_link = message.text
    
    try:
        wormhole_url = await process_magnet(magnet_link)
        if wormhole_url:
            await msg.edit_text(f"✅ Файл готов к скачиванию:\n{wormhole_url}")
        else:
            await msg.edit_text("❌ Не удалось обработать файл")
    except Exception as e:
        await msg.edit_text(f"⚠️ Произошла ошибка: {str(e)}")
    finally:
        # Additional cleanup if needed
        pass

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
