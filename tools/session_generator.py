# Run this locally to generate your session string
# pip install pyrogram TgCrypto

from pyrogram import Client

API_ID = input("Enter your API_ID: ")
API_HASH = input("Enter your API_HASH: ")

with Client("session_gen", api_id=int(API_ID), api_hash=API_HASH) as app:
    print("\n\n✅ Your SESSION_STRING (copy everything below):\n")
    print(app.export_session_string())
    print("\n")
