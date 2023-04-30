import telethon
from telethon import TelegramClient, events, sync
from telethon.tl.types import *
from telethon.tl.functions.messages import GetAllStickersRequest, SetTypingRequest
from telethon.tl.functions.messages import GetStickerSetRequest
from telethon.tl.types import InputStickerSetID
from telethon.tl.functions.messages import SendReactionRequest
import types
import emoji
import random
import time
import asyncio
import json

DEBUG = False
TIMESTAMPS = True
SHOW_ALL_INCOMING_MESSAGES = False
SHOW_ALL_OUTGOING_MESSAGES = False
USERS_REPLIES_ENABLED = True
CHANNELS_REPLIES_ENABLED = True

api_id = "YOUR_API_ID"
api_hash = "YOUR_API_HASH"

client = TelegramClient('anon', api_id, api_hash)

with open("user_replies.json", "r") as user_replies_json_file, \
        open("channel_replies.json", "r") as channel_replies_json_file:
    user_replies = json.load(user_replies_json_file)
    channel_replies = json.load(channel_replies_json_file)

user_chats = [int(i) if i.isdigit() else i for i in user_replies]
channel_chats = [int(i) if (i[0] == "-" and i[1:].isdigit()) or i.isdigit() else i for i in channel_replies]

if DEBUG:
    print("Got list of user chats:", user_chats, sep="\n")
    print("Got list of channels:", channel_chats, sep="\n")


def replies_format(replies):
    if "default" in replies:
        for entity in replies["default"]:
            for user in replies:
                if user != "default":
                    for var1 in replies["default"]:
                        if var1 not in replies[user]:
                            replies[user][var1] = replies["default"][var1]
                        else:
                            for var2 in replies["default"][var1]:
                                if var2 not in replies[user][var1]:
                                    replies[user][var1][var2] = replies["default"][var1][var2]

    for user in replies:
        for var1 in replies[user]:
            for var2 in replies[user][var1]:
                if var2 == "settings":
                    for var3 in replies[user][var1][var2]:
                        if (var3 == "responses" or "delay" in var3) and not isinstance(replies[user][var1][var2][var3],
                                                                                       list):
                            replies[user][var1][var2][var3] = [int(replies[user][var1][var2][var3]),
                                                               int(replies[user][var1][var2][var3])]
                else:
                    if not isinstance(replies[user][var1][var2], list):
                        replies[user][var1][var2] = [str(replies[user][var1][var2])]


replies_format(user_replies)
replies_format(channel_replies)

if DEBUG:
    print("Formated user replies:", user_replies, sep="\n")
    print("Formated channel replies:", channel_replies, sep="\n")


def user_exists(user):
    return user in user_chats


def channel_exists(channel):
    return channel in channel_chats


async def get_info(event):
    chat = await event.get_chat()
    sender = await event.get_sender()
    chat_id = event.chat_id
    sender_id = event.sender_id
    return chat, sender, chat_id, sender_id


def get_user(user_name, user_id):
    if user_exists(user_name):
        return user_name
    if user_exists(user_id):
        return user_id


async def reply(event, replies, user, var, reply_type=None):
    user_key = str(user)
    if DEBUG:
        print("user_key = ", user_key)
    if var not in replies[user_key]:
        return
    settings = "settings" in replies[user_key][var]
    realistic = settings and "realistic" in replies[user_key][var] and replies[user_key][var]["realistic"]
    reaction_delay = realistic and "reaction_delay" in replies[user_key][var]["settings"]
    mark_read = settings and "mark_read" in user_replies[user_key][var]["settings"] and user_replies[user_key][var]["settings"]["mark_read"]
    reaction = settings and "reaction_chance" in replies[user_key][var]["settings"] and \
               "reactions" in replies[user_key][var]
    response_delay = realistic and "response_delay" in replies[user_key][var]["settings"]
    responses = random.randint(*replies[user_key][var]["settings"]["responses"]) \
        if settings and "responses" in replies[user_key][var]["settings"] else 1
    sticker_chance = settings and "sticker_chance" in replies[user_key][var]["settings"]
    endings = "endings" in replies[user_key][var] and \
              (not settings or (settings and ("endings" not in replies[user_key][var]["settings"] or
                                              ("endings" in replies[user_key][var]["settings"] and
                                               replies[user_key][var]["settings"]["endings"]))))
    capitalize_chance = settings and "capitalize_chance" in replies[user_key][var]["settings"]
    reply_chance = settings and "reply_chance" in replies[user_key][var]["settings"]
    between_delay = settings and "between_delay" in replies[user_key][var]["settings"]
    if reply_type is None:
        if event.message.media is None:
            reply_type = "text"
        elif isinstance(event.message.media, MessageMediaDocument):
            print("event.message.media.document.mime_type =", event.message.media.document.mime_type)
            if event.message.media.document.mime_type == 'audio/ogg':
                reply_type = "audio"
            elif event.message.media.document.mime_type == 'video/mp4':
                reply_type = "video"
            elif event.message.media.document.mime_type in ['video/webm', 'application/x-tgsticker']:
                reply_type = "sticker"
        else:
            reply_type = "picture"
    if DEBUG:
        print("reply_type =", reply_type)
    if reply_type is not None and reply_type in replies[user_key][var]:
        if reaction_delay:
            await asyncio.sleep(random.randint(*replies[user_key][var]["settings"]["reaction_delay"]))
        if mark_read:
            event.message.mark_read()
        if reaction and random.randint(1, 100) <= replies[user_key][var]["settings"]["reaction_chance"]:
            await client(telethon.tl.functions.messages.SendReactionRequest(
                peer=user,
                msg_id=event.message.id,
                reaction=[telethon.tl.types.ReactionEmoji(
                    emoticon=random.choice(replies[user_key][var]["reactions"])
                )]
            ))
        if realistic:
            await client(telethon.tl.functions.messages.SetTypingRequest(
                peer=user,
                action=telethon.types.SendMessageTypingAction()
            ))
        if response_delay:
            await asyncio.sleep(random.randint(*replies[user_key][var]["settings"]["response_delay"]))
        for i in range(responses):
            if sticker_chance and random.randint(1, 100) <= replies[user_key][var]["settings"]["sticker_chance"]:
                sticker_sets = await client(GetAllStickersRequest(0))
                # sticker_set = random.choice(sticker_sets.sets)
                sticker_set = sticker_sets.sets[0]
                stickers_ = await client(GetStickerSetRequest(
                    stickerset=InputStickerSetID(
                        id=sticker_set.id, access_hash=sticker_set.access_hash
                    ),
                    hash=0
                ))
                await client.send_file(user, random.choice(stickers_.documents))
            else:
                response = random.choice(replies[user_key][var][reply_type])
                if endings:
                    response += random.choice(replies[user_key][var]["endings"])
                if capitalize_chance and \
                        random.randint(1, 100) <= replies[user_key][var]["settings"]["capitalize_chance"]:
                    response = response.capitalize()
                if (reply_chance and random.randint(1, 100) <= replies[user_key][var]["settings"]["reply_chance"]) or \
                        not reply_chance:
                    await event.reply(response)
                else:
                    await client.send_message(user, response)
            if realistic:
                await client(telethon.tl.functions.messages.SetTypingRequest(
                    peer=user,
                    action=telethon.types.SendMessageTypingAction()
                ))
            if realistic and between_delay:
                await asyncio.sleep(random.randint(*replies[user_key][var]["settings"]["between_delay"]))


if SHOW_ALL_INCOMING_MESSAGES:
    @client.on(events.NewMessage(incoming=True))
    async def all_incoming_messages_handler(event):
        chat = await event.get_chat()
        sender = await event.get_sender()
        DM = isinstance(chat, telethon.types.User)
        if DM:
            print(datetime.now().strftime("[%H:%M:%S] ") if TIMESTAMPS else "",
                  f"You have an incoming direct message from {sender.username if sender.username else event.sender_id}",
                  sep="")
        else:
            print(datetime.now().strftime("[%H:%M:%S] ") if TIMESTAMPS else "",
                  f"You have an incoming message in {chat.title if chat.title else chat.id} channel "
                  f"from {sender.username if sender.username else event.sender_id}", sep="")
        if DEBUG:
            print("Chat class:", chat)
            print("Sender class:", sender)
            print("Message class:", event.message)
            print("Text:", end=" ")
        print(event.message.message)
        print()


if SHOW_ALL_OUTGOING_MESSAGES:
    @client.on(events.NewMessage(outgoing=True))
    async def all_outgoing_messages_handler(event):
        chat = await event.get_chat()
        sender = await event.get_sender()
        DM = isinstance(chat, telethon.types.User)
        if DM:
            print(datetime.now().strftime("[%H:%M:%S] ") if TIMESTAMPS else "",
                  f"You sent a direct message to {chat.username if chat.username else chat.id}", sep="")
        else:
            print(datetime.now().strftime("[%H:%M:%S] ") if TIMESTAMPS else "",
                  f"You sent a message to {chat.title if chat.title else chat.id} channel", sep="")
        if DEBUG:
            print("Chat class:", chat)
            print("Sender class:", sender)
            print("Message class:", event.message)
        print("Text:", event.message.message)
        print()

if USERS_REPLIES_ENABLED:
    @client.on(events.NewMessage(incoming=True, chats=user_chats))
    async def users_user_handler(event):
        chat, sender, chat_id, sender_id = await get_info(event)
        user = get_user(sender.username, sender_id)
        print(datetime.now().strftime("[%H:%M:%S] ") if TIMESTAMPS else "",
              f"Handling {sender.username if sender.username else sender_id}'s message in DM is in process...", sep="")
        await reply(event, user_replies, user, "user")
        print(datetime.now().strftime("[%H:%M:%S] ") if TIMESTAMPS else "",
              f"Handling {sender.username if sender.username else sender_id}'s message in DM is done.", sep="")


    @client.on(events.NewMessage(outgoing=True, chats=user_chats))
    async def users_me_handler(event):
        chat, sender, chat_id, sender_id = await get_info(event)
        user = get_user(chat.username, chat_id)
        print(datetime.now().strftime("[%H:%M:%S] ") if TIMESTAMPS else "",
              f"Handling my message in DM with {chat.username if chat.username else chat_id} is in process...", sep="")
        await reply(event, user_replies, user, "me")
        print(datetime.now().strftime("[%H:%M:%S] ") if TIMESTAMPS else "",
              f"Handling my message in DM with {chat.username if chat.username else chat_id} is done.", sep="")

if CHANNELS_REPLIES_ENABLED:
    @client.on(events.NewMessage(incoming=True, chats=channel_chats))
    async def channels_user_handler(event):
        chat, sender, chat_id, sender_id = await get_info(event)
        print(datetime.now().strftime("[%H:%M:%S] ") if TIMESTAMPS else "",
              f"Handling {sender.username if sender.username else sender_id}'s message "
              f"in {chat.title if chat.title else chat_id} channel is in process...",
              sep="")
        await reply(event, channel_replies, chat_id, "user")
        print(datetime.now().strftime("[%H:%M:%S] ") if TIMESTAMPS else "",
              f"Handling {sender.username if sender.username else sender_id}'s message "
              f"in {chat.title if chat.title else chat_id} channel is done.",
              sep="")


    @client.on(events.NewMessage(outgoing=True, chats=channel_chats))
    async def channel_me_handler(event):
        chat, sender, chat_id, sender_id = await get_info(event)
        if sender
        print(datetime.now().strftime("[%H:%M:%S] ") if TIMESTAMPS else "",
              f"Handling my message in {chat.title if chat.title else chat_id} channel is in process...", sep="")
        await reply(event, channel_replies, chat_id, "me")
        print(datetime.now().strftime("[%H:%M:%S] ") if TIMESTAMPS else "",
              f"Handling my message in {chat.title if chat.title else chat_id} channel is done.", sep="")


client.start()
client.run_until_disconnected()