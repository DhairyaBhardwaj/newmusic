# Telegram Video Chat Music Bot

## Quick Start

1. Get your credentials:
   - API_ID & API_HASH from https://my.telegram.org
   - BOT_TOKEN from @BotFather
   - SESSION_STRING using tools/session_generator.py

2. Deploy to Render:
   - Push this folder to GitHub
   - Create a Background Worker on Render
   - Use Docker runtime
   - Add environment variables

## Environment Variables

- API_ID: Your Telegram API ID
- API_HASH: Your Telegram API Hash
- BOT_TOKEN: Bot token from @BotFather
- SESSION_STRING: Generated from session_generator.py

## Commands

- /play <song> - Play a song
- /pause - Pause playback
- /resume - Resume playback
- /skip - Skip current song
- /stop - Stop and leave
- /queue - View queue
- /nowplaying - Current song
- /volume <1-200> - Set volume
