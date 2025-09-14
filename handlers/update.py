import logging
from datetime import datetime

from common.nats_server import nc
from common.mysql import MySQL as db
from common.telegram import TelegramBot as tg

logger = logging.getLogger()

async def handle_chat(chat_data:dict):
    
    chat_id = chat_data["id"]
    title = chat_data.get("title", '')

    query = """
    INSERT INTO `kopilot_telegram`.`chat` (
        `chat_id`, `title`
    ) VALUES (%s, %s)
    ON DUPLICATE KEY UPDATE
        `title` = IF(VALUES(`title`) != '', VALUES(`title`), `title`);
    """
    last_id = await db.aexecute_insert(
        query,
        (chat_id, title)
    )
    if not last_id:
        logger.info(f"Updated chat {chat_id} in database.")
    else:
        logger.info(f"Inserted chat {chat_id} in database.")
        # TODO: get more data
    
    return chat_id


async def handle_user(user_data: dict):

    user_id = user_data["id"]
    first_name = user_data.get("first_name", '')
    last_name = user_data.get("last_name", '')
    username = user_data.get("username")
    is_bot = user_data.get("is_bot", False)

    query = """
    INSERT INTO `kopilot_telegram`.`user` (
        `user_id`,
        `first_name`,
        `last_name`,
        `username`,
        `is_bot`
    )
    VALUES (%s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE 
        `first_name` = IF(VALUES(`first_name`) != '', VALUES(`first_name`), `first_name`),
        `last_name` = IF(VALUES(`last_name`) != '', VALUES(`last_name`), `last_name`),
        `username` = VALUES(`username`),
        `is_bot` = VALUES(`is_bot`);
    """
    last_id = await db.aexecute_insert(
        query,
        (user_id, first_name, last_name, username, is_bot)
    )
    if not last_id:
        logger.info(f"Updated user {user_id} in database.")
    else:
        logger.info(f"Inserted user {user_id} in database.")
        # TODO: get more data
    
    return user_id


async def handle_message(message_data: dict):

    message_id = message_data.get("message_id")
    user_data = message_data.get("from", {})
    if not user_data:
        return

    chat_data = message_data.get("chat", {})

    message_timestamp = message_data.get("date")
    message_date = datetime.fromtimestamp(message_timestamp)

    user_id = await handle_user(user_data)

    chat_type = chat_data.get('type')
    if chat_type == "private":
        text = message_data.get('text')
        if text:
            logger.info("Received KoTube query")
            await nc.pub(
                "youtube.query",
                {
                    "user_id": user_id,
                    "query": text,
                    "timestamp": datetime.now().isoformat()
                }
            )
        
    elif chat_type in ('group', 'supergroup'):
        chat_id = await handle_chat(chat_data)


@nc.sub("telegram.update")
async def update(data: dict):
    
    event_id = data.get("event_id")
    update_data = data.get("update", {})

    try:
        message_data = update_data.get("message", {})
        if message_data:
            logger.info(f"Processing message component for update {event_id}")
            await handle_message(message_data)

        message_reaction = update_data.get("message_reaction", {})

        my_chat_member = update_data.get("my_chat_member", {})

        chat_member = update_data.get("chat_member", {})

        await nc.pub(
            "telegram.update.processed",
            {
                "event_id": event_id,
                "timestamp": datetime.now().isoformat()
            }
        )
    except Exception as e:
        logger.error(f"Error processing update {event_id}")
        await nc.pub(
            "telegram.update.error_processing",
            {
                "event_id": event_id,
                "timestamp": datetime.now().isoformat(),
                "error_message": str(e)
            }
        )

    ...