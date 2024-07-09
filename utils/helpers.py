import asyncio 
from info import *
from pyrogrimport asyncio 
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from pyrogram.errors import UserNotParticipant
from pyrogram.types import ChatPermissions
from pymongo.errors import DuplicateKeyError
from motor.motor_asyncio import AsyncIOMotorClient
from imdb import Cinemagoer
from pyrogram import enums

# Initialize MongoDB client and collections
DATABASE_URI = "your_database_uri"
dbclient = AsyncIOMotorClient(DATABASE_URI)
db = dbclient["Channel-Filter"]
grp_col = db["GROUPS"]
user_col = db["USERS"]
dlt_col = db["Auto-Delete"]

ia = Cinemagoer()

# Function to add a group to MongoDB
async def add_group(group_id, group_name, user_name, user_id, channels, f_sub, verified):
    data = {
        "_id": group_id,
        "name": group_name, 
        "user_id": user_id,
        "user_name": user_name,
        "channels": channels,
        "f_sub": f_sub,
        "verified": verified
    }
    try:
       await grp_col.insert_one(data)
    except DuplicateKeyError:
       pass

# Function to get a group from MongoDB
async def get_group(id):
    data = {'_id': id}
    group = await grp_col.find_one(data)
    if group is None:
        return {}
    return dict(group)

# Function to update group data in MongoDB
async def update_group(id, new_data):
    data = {"_id": id}
    new_value = {"$set": new_data}
    await grp_col.update_one(data, new_value)

# Function to delete a group from MongoDB
async def delete_group(id):
    data = {"_id": id}
    await grp_col.delete_one(data)

# Function to get all groups from MongoDB
async def get_groups():
    count = await grp_col.count_documents({})
    cursor = grp_col.find({})
    list = await cursor.to_list(length=int(count))
    return count, list

# Function to add a user to MongoDB
async def add_user(id, name):
    data = {"_id": id, "name": name}
    try:
       await user_col.insert_one(data)
    except DuplicateKeyError:
       pass

# Function to get all users from MongoDB
async def get_users():
    count = await user_col.count_documents({})
    cursor = user_col.find({})
    list = await cursor.to_list(length=int(count))
    return count, list

# Function to save a deleted message to MongoDB
async def save_dlt_message(message, time):
    data = {
        "chat_id": message.chat.id,
        "message_id": message.message_id,
        "time": time
    }
    await dlt_col.insert_one(data)

# Function to get all deleted messages from MongoDB
async def get_all_dlt_data(time):
    data = {"time": {"$lte": time}}
    count = await dlt_col.count_documents(data)
    cursor = dlt_col.find(data)
    all_data = await cursor.to_list(length=int(count))
    return all_data

# Function to delete all expired deleted messages from MongoDB
async def delete_all_dlt_data(time):
    data = {"time": {"$lte": time}}
    await dlt_col.delete_many(data)

# Function to search IMDb for movies
async def search_imdb(query):
    try:
        int(query)
        movie = ia.get_movie(query)
        return movie["title"]
    except:
        movies = ia.search_movie(query, results=10)
        list = []
        for movie in movies:
            title = movie["title"]
            try:
                year = f" - {movie['year']}"
            except:
                year = ""
            list.append({"title": title, "year": year, "id": movie.movieID})
        return list

# Function to enforce subscription in a group
async def force_sub(bot, message):
    group = await get_group(message.chat.id)
    if not group:
        return False

    f_sub = group.get("f_sub", False)
    admin = group.get("user_id", None)
    if not f_sub or not admin:
        return True
    
    if message.from_user is None:
        return True
    
    try:
        f_link = (await bot.get_chat(f_sub)).invite_link
        member = await bot.get_chat_member(f_sub, message.from_user.id)
        if member.status == enums.ChatMemberStatus.BANNED:
            await message.reply(f"Sorry {message.from_user.mention}!\n You are banned in our channel, you will be banned from here within 10 seconds")
            await asyncio.sleep(10)
            await bot.ban_chat_member(message.chat.id, message.from_user.id)
            return False
    except UserNotParticipant:
        await bot.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=message.from_user.id,
            permissions=ChatPermissions(can_send_messages=False)
        )
        await message.reply(
            f"⚠ Dear User {message.from_user.mention}!\n\nTo send messages in this group, you must join our channel.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Join Channel", url=f_link)],
                [InlineKeyboardButton("Try Again", callback_data=f"checksub_{message.from_user.id}")]
            ])
        )
        await message.delete()
        return False
    except Exception as e:
        if admin:
            await bot.send_message(chat_id=admin, text=f"❌ Error in Fsub:\n`{str(e)}`")
        return False
    else:
        return True

# Example usage with Pyrogram Client
app = Client("my_bot")

@app.on_message(filters.command("start"))
async def start_command(client, message):
    await message.reply("Hello! I am your bot.")

@app.on_message(filters.text)
async def auto_delete(client, message):
    await save_dlt_message(message, time=300)  # Save the message to delete after 5 minutes
    await asyncio.sleep(300)  # Wait for 5 minutes
    await message.delete()  # Delete the message

@app.on_message(filters.command("checksub"))
async def check_subscription(client, message):
    await force_sub(client, message)

app.run()
