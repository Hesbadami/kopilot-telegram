import logging
from datetime import datetime

from common.nats_server import nc
from common.mysql import MySQL as db

logger = logging.getLogger()

async def handle_chat(chat_data:dict):
    ...

async def handle_user(user_data: dict):
    ...

async def handle_message(message_data: dict):

    message_id = message_data.get("message_id")
    user_data = message_data.get("from", {})
    chat_data = message_data.get("chat", {})

    message_timestamp = message_data.get("date")
    message_date = datetime.fromtimestamp(message_timestamp)

    user = await handle_user(user_data)

    chat_type = chat_data.get('type')
    if chat_type == "private":
        text = message_data.get('text')
        if text:
            logger.info("Received KoTube query")
            nc.pub(
                "youtube.query",
                {
                    "user_id": user['user_id'],
                    "query": text,
                    "timestamp": datetime.now().isoformat()
                }
            )
        ...


    chat = await handle_chat(chat_data)

    return True


    ...

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

        nc.pub(
            "telegram.update.processed",
            {
                "event_id": event_id,
                "timestamp": datetime.now().isoformat()
            }
        )
    except Exception as e:

        nc.pub(
            "telegram.update.error_processing",
            {
                "event_id": event_id,
                "timestamp": datetime.now().isoformat(),
                "error_message": str(e)
            }
        )

    ...