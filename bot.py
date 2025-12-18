import os
import asyncio
from aiohttp import web
from pyrofork import Client, filters
from pyrofork.types import Message
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream
import yt_dlp

# Environment variables
API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "")
PORT = int(os.environ.get("PORT", 8080))

# Initialize clients
app = Client("music_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
user = Client("user_session", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)
pytgcalls = PyTgCalls(user)

# Store for current songs and queues
queues = {}
current_song = {}


# Web server for Render health checks
async def health_check(request):
    return web.json_response({"status": "alive", "bot": "running"})

async def home(request):
    return web.Response(text="🎵 Telegram Music Bot is running!")

web_app = web.Application()
web_app.router.add_get("/", home)
web_app.router.add_get("/health", health_check)


def get_youtube_audio(query: str) -> dict | None:
    """Search and get audio URL from YouTube."""
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
        'extract_flat': False,
        'default_search': 'ytsearch',
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            if not query.startswith("http"):
                query = f"ytsearch:{query}"
            info = ydl.extract_info(query, download=False)
            
            if 'entries' in info:
                info = info['entries'][0]
            
            return {
                'url': info['url'],
                'title': info.get('title', 'Unknown'),
                'duration': info.get('duration', 0),
                'thumbnail': info.get('thumbnail', ''),
            }
    except Exception as e:
        print(f"YouTube error: {e}")
        return None


async def play_song(chat_id: int, song_info: dict):
    """Play a song in the video chat."""
    try:
        current_song[chat_id] = song_info
        await pytgcalls.play(
            chat_id,
            MediaStream(song_info['url'])
        )
        return True
    except Exception as e:
        print(f"Play error: {e}")
        return False


async def process_queue(chat_id: int):
    """Process the next song in queue."""
    if chat_id in queues and queues[chat_id]:
        next_song = queues[chat_id].pop(0)
        await play_song(chat_id, next_song)
        return next_song
    return None


@app.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    await message.reply(
        "🎵 **Music Bot for Video Chats**\n\n"
        "**Commands:**\n"
        "/play <song name/URL> - Play a song\n"
        "/pause - Pause playback\n"
        "/resume - Resume playback\n"
        "/skip - Skip to next song\n"
        "/stop - Stop and leave\n"
        "/queue - View queue\n"
        "/nowplaying - Current song\n"
        "/volume <1-200> - Set volume\n\n"
        "Add me to a group and start a video chat!"
    )


@app.on_message(filters.command("play") & filters.group)
async def play_command(client: Client, message: Message):
    chat_id = message.chat.id
    
    if len(message.command) < 2:
        await message.reply("❌ Please provide a song name or URL.\n\nUsage: /play <song name>")
        return
    
    query = " ".join(message.command[1:])
    status_msg = await message.reply(f"🔍 Searching for: **{query}**...")
    
    song_info = get_youtube_audio(query)
    
    if not song_info:
        await status_msg.edit("❌ Could not find the song. Try a different search.")
        return
    
    # Check if already playing
    if chat_id in current_song and current_song[chat_id]:
        if chat_id not in queues:
            queues[chat_id] = []
        queues[chat_id].append(song_info)
        await status_msg.edit(
            f"📋 Added to queue: **{song_info['title']}**\n"
            f"Position: {len(queues[chat_id])}"
        )
        return
    
    success = await play_song(chat_id, song_info)
    
    if success:
        duration = f"{song_info['duration'] // 60}:{song_info['duration'] % 60:02d}" if song_info['duration'] else "Unknown"
        await status_msg.edit(
            f"🎵 **Now Playing**\n\n"
            f"**{song_info['title']}**\n"
            f"Duration: {duration}"
        )
    else:
        await status_msg.edit("❌ Failed to play. Make sure a video chat is active!")


@app.on_message(filters.command("pause") & filters.group)
async def pause_command(client: Client, message: Message):
    try:
        await pytgcalls.pause_stream(message.chat.id)
        await message.reply("⏸ Paused")
    except Exception as e:
        await message.reply(f"❌ Error: {e}")


@app.on_message(filters.command("resume") & filters.group)
async def resume_command(client: Client, message: Message):
    try:
        await pytgcalls.resume_stream(message.chat.id)
        await message.reply("▶️ Resumed")
    except Exception as e:
        await message.reply(f"❌ Error: {e}")


@app.on_message(filters.command("skip") & filters.group)
async def skip_command(client: Client, message: Message):
    chat_id = message.chat.id
    
    next_song = await process_queue(chat_id)
    
    if next_song:
        await message.reply(f"⏭ Skipped! Now playing: **{next_song['title']}**")
    else:
        try:
            await pytgcalls.leave_call(chat_id)
            current_song.pop(chat_id, None)
            await message.reply("⏭ Skipped! Queue is empty.")
        except:
            await message.reply("❌ Nothing to skip.")


@app.on_message(filters.command("stop") & filters.group)
async def stop_command(client: Client, message: Message):
    chat_id = message.chat.id
    try:
        await pytgcalls.leave_call(chat_id)
        current_song.pop(chat_id, None)
        queues.pop(chat_id, None)
        await message.reply("⏹ Stopped and left the video chat.")
    except Exception as e:
        await message.reply(f"❌ Error: {e}")


@app.on_message(filters.command("queue") & filters.group)
async def queue_command(client: Client, message: Message):
    chat_id = message.chat.id
    
    if chat_id not in queues or not queues[chat_id]:
        await message.reply("📋 Queue is empty.")
        return
    
    queue_text = "📋 **Current Queue**\n\n"
    for i, song in enumerate(queues[chat_id][:10], 1):
        queue_text += f"{i}. {song['title']}\n"
    
    if len(queues[chat_id]) > 10:
        queue_text += f"\n... and {len(queues[chat_id]) - 10} more"
    
    await message.reply(queue_text)


@app.on_message(filters.command("nowplaying") & filters.group)
async def nowplaying_command(client: Client, message: Message):
    chat_id = message.chat.id
    
    if chat_id not in current_song or not current_song[chat_id]:
        await message.reply("🎵 Nothing is playing right now.")
        return
    
    song = current_song[chat_id]
    duration = f"{song['duration'] // 60}:{song['duration'] % 60:02d}" if song.get('duration') else "Unknown"
    
    await message.reply(
        f"🎵 **Now Playing**\n\n"
        f"**{song['title']}**\n"
        f"Duration: {duration}"
    )


@app.on_message(filters.command("volume") & filters.group)
async def volume_command(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply("❌ Usage: /volume <1-200>")
        return
    
    try:
        vol = int(message.command[1])
        if not 1 <= vol <= 200:
            raise ValueError()
        
        await pytgcalls.change_volume_call(message.chat.id, vol)
        await message.reply(f"🔊 Volume set to {vol}%")
    except ValueError:
        await message.reply("❌ Please provide a number between 1-200")
    except Exception as e:
        await message.reply(f"❌ Error: {e}")


@pytgcalls.on_stream_end()
async def on_stream_end(client: PyTgCalls, update):
    chat_id = update.chat_id
    next_song = await process_queue(chat_id)
    
    if not next_song:
        current_song.pop(chat_id, None)


async def start_web_server():
    """Start the web server for Render health checks."""
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"Web server started on port {PORT}")


async def main():
    # Start web server first (for Render health checks)
    await start_web_server()
    
    # Start Telegram clients
    await user.start()
    await app.start()
    await pytgcalls.start()
    print("Bot started!")
    
    # Keep running
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
