import logging
from datetime import datetime
from typing import Union
from collections import Counter
import io

from common.nats_server import nc
from common.mysql import MySQL as db
from common.telegram import TelegramBot as tg
from common.config import MEDIA_PATH, TELEGRAM_TOKEN

import httpx
from anyio import Path, open_file, to_thread
from PIL import Image

logger = logging.getLogger()

def extract_dominant_color(image_bytes):
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img = img.convert('RGB')
        img = img.resize((100, 100))
        
        pixels = list(img.getdata())
        most_common = Counter(pixels).most_common(1)[0][0]
        
        return f"#{most_common[0]:02x}{most_common[1]:02x}{most_common[2]:02x}"
        
    except Exception as e:
        logger.error(f"Failed to extract dominant color: {str(e)}")
        return "#000000"

async def download_user_photo(user, file_id):
    file_info = await tg.call("getFile", file_id=file_id)
    if not file_info:
        logger.error(f"Failed to get file info for profile photo: {user['user_id']}")
        return
    
    file_path = file_info.get('file_path')
    if not file_path:
        logger.error("No file path in file info")
        return
    
    file_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            file_response = await client.get(file_url)
            file_response.raise_for_status()

            image_bytes = file_response.content

            filename = f"{user['user_id']}.jpg"
            file_path_local = Path(MEDIA_PATH, 'user', filename)

            await file_path_local.write_bytes(image_bytes)

            query = """
            UPDATE `kopilot_telegram`.`user`
            SET 
                `photo` = %s,
                `photo_file_id` = %s
            WHERE `user_id` = %s;
            """
            relative_path = f"user/{filename}"
            params = (relative_path, file_id, user['user_id'])
            await db.aexecute_update(query, params)
            
            logger.info(f"Downloaded profile photo for user {user['user_id']} to {file_path_local}")

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error downloading profile photo for user {user['user_id']}: {e.response.status_code}")
    except httpx.TimeoutException:
        logger.error(f"Timeout downloading profile photo for user {user['user_id']}")
    except Exception as e:
        logger.error(f"Failed to download profile photo for user {user['user_id']}: {str(e)}")
        
async def download_chat_photo(chat, file_id):
    file_info = await tg.call("getFile", file_id=file_id)
    if not file_info:
        logger.error(f"Failed to get file info for chat photo: {chat['chat_id']}")
        return
    
    file_path = file_info.get('file_path')
    if not file_path:
        logger.error("No file path in file info")
        return
    
    file_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            file_response = await client.get(file_url)
            file_response.raise_for_status()

            image_bytes = file_response.content
            accent_color = await to_thread.run_sync(extract_dominant_color, image_bytes)

            filename = f"{chat['chat_id']}.jpg"
            file_path_local = Path(MEDIA_PATH, 'chat', filename)
            
            await file_path_local.write_bytes(image_bytes)

            query = """
            UPDATE `kopilot_telegram`.`chat`
            SET 
                `photo` = %s,
                `photo_file_id` = %s,
                `accent_color` = %s,
            WHERE `chat_id` = %s;
            """
            relative_path = f"chat/{filename}"
            params = (relative_path, file_id, accent_color, chat['chat_id'])
            await db.aexecute_update(query, params)
            
            logger.info(f"Downloaded chat photo for chat {chat['chat_id']} to {file_path_local}")

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error downloading chat photo for chat {chat['chat_id']}: {e.response.status_code}")
    except httpx.TimeoutException:
        logger.error(f"Timeout downloading chat photo for chat {chat['chat_id']}")
    except Exception as e:
        logger.error(f"Failed to download chat photo for chat {chat['chat_id']}: {str(e)}")


@nc.sub("telegram.sync.user")
async def sync_user(data: dict):

    user_id = data['user_id']
    user = await db.aexecute_query(
        "SELECT * FROM `kopilot_telegram`.`user` WHERE user_id = %s LIMIT 1;",
        (user_id,),
        fetch_one=True
    )
    if not user:
        logger.warning(f"Attempted sync on non existing user: {user_id}.")
        return

    photos = await tg.call("getUserProfilePhotos", user_id=user_id)
    if photos and photos.get("photos"):
        photo = photos["photos"][0][-1]
        file_id = photo.get("file_id")

        if file_id != user['photo_file_id']:
            await download_user_photo(user, file_id)


@nc.sub("telegram.sync.chat")
async def sync_chat(data: dict):

    chat_id = data['chat_id']
    chat = await db.aexecute_query(
        "SELECT * FROM `kopilot_telegram`.`chat` WHERE chat_id = %s LIMIT 1;",
        (chat_id,),
        fetch_one=True
    )
    if not chat:
        logger.warning(f"Attempted sync on non existing chat: {chat_id}.")
        return

    chat_data = await tg.call("getChat", chat_id=chat_id)
    if chat_data:
        title = chat_data.get("title", chat['title'])
        invite_link = chat_data.get("invite_link", chat['invite_link'])

        query = """
        UPDATE `kopilot_telegram`.`chat`
        SET
            `title` = %s,
            `invite_link` = %s
        WHERE `chat_id` = %s;
        """
        params = (title, invite_link, chat_id)
        updated = await db.aexecute_update(query, params)

        photo = chat_data.get("photo", {})

        if photo:
            file_id = photo.get("big_file_id")
            if file_id and file_id != chat['photo_file_id']:
                await download_chat_photo(chat, file_id)
    

@nc.sub("telegram.sync.chatmember")
async def sync_chatmember(data: dict):
    
    user_id = data['user_id']
    chat_id = data['chat_id']
    timestamp = datetime.fromisoformat(data['timestamp'])
    performer = data.get("performer")

    query = """
    SELECT * FROM `kopilot_telegram`.`chatmember`
    WHERE user_id = %s AND chat_id = %s LIMIT 1;
    """
    chatmember = await db.aexecute_query(
        query,
        (user_id, chat_id),
        fetch_one=True
    )
    if not chatmember:
        logger.warning(f"Attempted sync on non existing chatmember: {user_id}, {chat_id}")
        return
    
    chatmember_data = await tg.call("getChatMember", user_id=user_id, chat_id=chat_id)
    status = chatmember_data.get("status", chatmember['status'])
    custom_title = chatmember_data.get("custom_title", chatmember['custom_title'])
    
    added_by = chatmember['added_by']
    removed_by = chatmember['removed_by']

    joined_at = chatmember['joined_at']
    left_at = chatmember['left_at']

    if chatmember['status'] not in ["member", "administrator", "creator"] and status in ["member", "administrator", "creator"]:
        joined_at = timestamp
        added_by = performer

    elif chatmember['status'] in ["member", "administrator", "creator"] and status not in ["member", "administrator", "creator"]:
        left_at = timestamp
        removed_by = performer
    
    query = """
    UPDATE `kopilot_telegram`.`chatmember`
    SET
        `status` = %s, 
        `custom_title` = %s, 
        `joined_at` = %s, 
        `left_at` = %s,
        `added_by` = %s,
        `removed_by` = %s
    WHERE `user_id` = %s AND `chat_id` = %s;
    """
    params = (
        status, custom_title, joined_at, left_at, 
        added_by, removed_by, user_id, chat_id
    )

    updated = await db.aexecute_update(
        query,
        params
    )
