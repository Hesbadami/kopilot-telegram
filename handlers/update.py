import logging
from datetime import datetime
from typing import Union

from common.nats_server import nc
from common.mysql import MySQL as db
from common.telegram import TelegramBot as tg

logger = logging.getLogger()


async def handle_chat(chat_data:dict) -> int:
    
    chat_id = int(chat_data["id"])
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
        await nc.pub(
            "telegram.sync.chat",
            {'chat_id': chat_id}
        )
    
    return chat_id


async def handle_user(user_data: dict) -> int:

    user_id = int(user_data["id"])
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
        await nc.pub(
            "telegram.sync.user",
            {'user_id': user_id}
        )

    return user_id

async def handle_chatmember(user_id: Union[int, str], chat_id: Union[int, str], event_time: datetime) -> int:

    user_id = int(user_id)
    chat_id = int(chat_id)

    chatmember = await db.aexecute_query(
        "SELECT `id` FROM `kopilot_telegram`.`chatmember` WHERE `user_id` = %s AND `chat_id` = %s LIMIT 1;",
        (user_id, chat_id),
        fetch_one = True
    )

    if chatmember:
        return chatmember['id']
    
    chatmember_data = await tg.call("getChatMember", user_id=user_id, chat_id=chat_id)
    status = chatmember_data.get("status", "member")
    custom_title = chatmember_data.get("custom_title")

    left_at = None
    if status not in ["member", "administrator", "creator"]:
        left_at = event_time

    query = """
    INSERT INTO `kopilot_telegram`.`chatmember` (
        `user_id`, `chat_id`, `status`, `custom_title`, `joined_at`, `left_at`
    ) VALUES (
        %s, %s, %s, %s, %s, %s
    );
    """

    chatmember_id = await db.aexecute_insert(
        query,
        (user_id, chat_id, status, custom_title, event_time, left_at)
    )

    return chatmember_id


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
        chatmember_id = await handle_chatmember(user_id, chat_id, message_date)
    
        query = """
        SELECT `id` FROM `kopilot_telegram`.`message`
        WHERE `chat_id` = %s AND `message_id` = %s LIMIT 1;
        """
        message_exists = await db.aexecute_query(
            query,
            (chat_id, message_id),
            fetch_one = True
        )
        if message_exists:
            logger.info(f"Message {message_id} already exists.")
            return

        message_type = "other"
        if "text" in message_data: 
            message_type = "text"
        elif "audio" in message_data:
            message_type = "audio"
        elif "video" in message_data: 
            message_type = "video"
        elif "video_note" in message_data: 
            message_type = "video_note"
        elif "voice" in message_data: 
            message_type = "voice"
        elif "animation" in message_data: 
            message_type = "animation"
        elif "document" in message_data: 
            message_type = "document"
        elif "photo" in message_data: 
            message_type = "photo"
        elif "sticker" in message_data: 
            message_type = "sticker"

        is_external_forward = False
        try:
            forward_from_id = message_data.get("forward_from", {}).get("id", None)
            if forward_from_id and int(forward_from_id) != int(user_id):
                is_external_forward = True
        except:
            pass
        
        reply_to_message_id = None
        reply_to_message = message_data.get("reply_to_message")
        if reply_to_message:
            reply_to_message_message_id = reply_to_message.get("message_id")
            query = """
            SELECT `id` FROM `kopilot_telegram`.`message`
            WHERE `chat_id` = %s AND `message_id` = %s LIMIT 1;
            """
            reply_to_message_id = await db.aexecute_query(
                query,
                (chat_id, reply_to_message_message_id),
                fetch_one = True
            )
            if reply_to_message_id:
                reply_to_message_id = reply_to_message_id['id']

        params = (
            message_id,
            chatmember_id,
            user_id,
            chat_id,
            message_date,
            reply_to_message_id,
            message_type,
            is_external_forward
        )
        query = """
        INSERT INTO `kopilot_telegram`.`message` (
            `message_id`,
            `chatmember_id`,
            `user_id`,
            `chat_id`,
            `date`,
            `reply_to_message_id`,
            `type`,
            `is_external_forward`
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s
        );
        """
        message_rowid = await db.aexecute_insert(
            query,
            params
        )
        logger.info(f"Inserted message {message_id} in database.")

        if not is_external_forward:
            await nc.pub(
                "analytics.ledger",
                {
                    'user_id': user_id,
                    'chat_id': chat_id,
                    'timestamp': message_date,
                    'type': message_type
                }
            )
            if reply_to_message_id:
                await nc.pub(
                    "analytics.ledger",
                    {
                        'user_id': user_id, 'chat_id': chat_id,
                        'timestamp': message_date, 'type': 'reply'
                    }
                )

        new_chat_members = message_data.get('new_chat_members')
        if new_chat_members:
            logger.info(f"Processing {len(new_chat_members)} new chat members")
            for new_chat_member in new_chat_members:
                new_user_id = await handle_user(new_chat_member)
                new_chatmember_id = await handle_chatmember(new_user_id, chat_id, message_date)
                await nc.pub(
                    "telegram.sync.chatmember",
                    {
                        'user_id': new_user_id,
                        'chat_id': chat_id,
                        'timestamp': message_date.isoformat()
                    }
                )

        left_chat_member = message_data.get('left_chat_member')
        if left_chat_member:
            logger.info(f"Processing left chat member")
            left_user_id = await handle_user(left_chat_member)
            left_chatmember_id = await handle_chatmember(left_user_id, chat_id, message_date)
            await nc.pub(
                "telegram.sync.chatmember",
                {
                    'user_id': left_user_id,
                    'chat_id': chat_id,
                    'timestamp': message_date.isoformat()
                }
            )

        if any(
            'new_chat_title' in message_data,
            'new_chat_photo' in message_data,
            'delete_chat_photo' in message_data
        ):
            await nc.pub(
                "telegram.sync.chat",
                {'chat_id': chat_id}
            )


async def handle_reaction(message_reaction: dict):

    message_id = message_reaction.get("message_id")
    user_data = message_reaction.get("user", {})
    if not user_data:
        return

    chat_data = message_reaction.get("chat", {})

    reaction_timestamp = message_reaction.get("date")
    reaction_date = datetime.fromtimestamp(reaction_timestamp)

    user_id = await handle_user(user_data)

    chat_type = chat_data.get('type')
    if chat_type in ('group', 'supergroup'):
        chat_id = await handle_chat(chat_data)
        chatmember_id = await handle_chatmember(user_id, chat_id, reaction_date)
    
        query = """
        SELECT `id` FROM `kopilot_telegram`.`message`
        WHERE `chat_id` = %s AND `message_id` = %s LIMIT 1;
        """
        message_row = await db.aexecute_query(
            query,
            (chat_id, message_id),
            fetch_one = True
        )
        if not message_row:
            logger.info(f"Message {message_id} does not exist.")
            return
        
        message_rowid = message_row['id']
        
        query = """
        SELECT `id` FROM `kopilot_telegram`.`reaction`
        WHERE `chat_id` = %s AND `message_id` = %s LIMIT 1;
        """
        reaction_exists = await db.aexecute_query(
            query,
            (chat_id, message_rowid),
            fetch_one = True
        )
        if reaction_exists:
            logger.info(f"Reaction already exists.")
            return
        
        is_deleted = False
        
        params = (
            message_rowid,
            chatmember_id,
            user_id,
            chat_id,
            reaction_date,
            is_deleted
        )
        query = """
        INSERT INTO `kopilot_telegram`.`reaction` (
            `message_id`,
            `chatmember_id`,
            `user_id`,
            `chat_id`,
            `date`,
            `is_deleted`
        ) VALUES (
            %s, %s, %s, %s, %s, %s
        );
        """
        reaction_rowid = await db.aexecute_insert(
            query,
            params
        )
        logger.info(f"Inserted reaction in database.")

        await nc.pub(
            "analytics.ledger",
            {
                'user_id': user_id,
                'chat_id': chat_id,
                'timestamp': reaction_date,
                'type': 'reaction'
            }
        )


async def handle_chatmember_updated(chatmember_updated: dict):
    user_data = chatmember_updated.get("from", {})
    chat_data = chatmember_updated.get("chat", {})

    timestamp = chatmember_updated.get("date")
    date = datetime.fromtimestamp(timestamp)

    user_id = await handle_user(user_data)

    new_chat_member_data = chatmember_updated.get("new_chat_member", {})
    new_chat_member_user_data = new_chat_member_data.get("user", {})
    new_user_id = await handle_user(new_chat_member_user_data)

    chat_type = chat_data.get('type')
    if chat_type in ('group', 'supergroup'):
        chat_id = await handle_chat(chat_data)
        chatmember_id = await handle_chatmember(user_id, chat_id, date)
        new_chatmember_id = await handle_chatmember(new_user_id, chat_id, date)
        await nc.pub(
            "telegram.sync.chatmember",
            {
                'user_id': new_user_id,
                'chat_id': chat_id,
                'timestamp': date.isoformat(),
                'performer': user_id
            }
        )


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
        if message_reaction:
            logger.info(f"Processing reaction for update {event_id}")
            await handle_reaction(message_reaction)

        my_chat_member = update_data.get("my_chat_member", {})
        if my_chat_member:
            logger.info(f"Processing my_chat_member component for update {event_id}")
            await handle_chatmember_updated(my_chat_member)

        chat_member = update_data.get("chat_member", {})
        if chat_member:
            logger.info(f"Processing chat_member component for update {event_id}")
            await handle_chatmember_updated(chat_member)

        callback_query = update_data.get("callback_query", {})
        if callback_query:
            logger.info(f"Processing callback query component for update {event_id}")
            await nc.pub(
                "youtube.callback",
                {
                    "query": callback_query,
                    "timestamp": datetime.now().isoformat()
                }
            )

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


@nc.sub("telegram.update.processed")
async def update_processed(data: dict):

    event_id = data.get('event_id')
    timestamp_str = data.get('timestamp')

    if not event_id or not timestamp_str:
        logger.critical(f"Missing required data: event_id={event_id}, timestamp={timestamp_str}")
        return

    try:
        timestamp = datetime.fromisoformat(timestamp_str)
    except ValueError as e:
        logger.critical(f"Invalid timestamp format: {timestamp_str}, error: {e}")
        return
    
    query = """
    UPDATE `kopilot_events`.`raw_events`
    SET 
        `processed` = TRUE, 
        `processed_at` = %s,
        `status` = 'done'
    WHERE `id` = %s;
    """
    params = (timestamp, event_id)
    updated = await db.aexecute_update(query, params)
    logger.info(f"Updated {updated} event rows as processed.")


@nc.sub("telegram.update.error_processing")
async def update_error_processing(data: dict):

    event_id = data.get('event_id')
    error_message = data.get('error_message')

    if not event_id:
        logger.critical(f"Missing required data: event_id={event_id}")
        return

    query = """
    UPDATE `kopilot_events`.`raw_events`
    SET 
        `status` = 'failed',
        `error_message` = %s,
        `retry_count` = `retry_count` + 1
    WHERE `id` = %s;
    """
    params = (error_message, event_id)
    updated = await db.aexecute_update(query, params)
    logger.info(f"Updated {updated} event rows as failed.")