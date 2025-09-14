import logging
from urllib.parse import quote
from typing import Optional, Dict, Any, Union
import json

from common.config import TELEGRAM_TOKEN

import anyio
from anyio import to_thread, Semaphore
import httpx
from asynciolimiter import StrictLimiter

logger = logging.getLogger("telegram")

class TelegramBot:

    api_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/"
    _rate_limiter = StrictLimiter(30/1)

    @classmethod
    async def call(cls, method: str, files: Optional[Dict] = None, **kwargs) -> Optional[Any]:
        
        await cls._rate_limiter.wait()

        url = f"{cls.api_url}{method}"
        logger.info(f"Making API call to {url} with parameters: {kwargs}")
        
        async with httpx.AsyncClient() as client:
            try:
                data = {}
                for key, value in kwargs.items():
                    if isinstance(value, (list, dict)):
                        data[key] = json.dumps(value)
                    else:
                        data[key] = value
                
                if files:
                    response = await client.post(url, data=data, files=files)
                else:
                    response = await client.post(url, data=data)
                    
                if response.status_code == 200:
                    response_data = response.json()
                    if not response_data.get('ok'):
                        logger.warning(f"API call to {url} failed with error: {response_data.get('description')}")
                        return None
                    
                    logger.info(f"API call to {url} succeeded")
                    return response_data.get('result')
                else:
                    logger.error(f"API call to {url} failed with status code {response.status_code} and response: {response.text}")
                    return None
                    
            except httpx.RequestError as e:
                logger.exception(f"An error occurred while making API call to {url}: {e}")
                return None

    @classmethod
    async def send_message(cls, chat_id: Union[int, str], text: str, **kwargs) -> Optional[Any]:
        if not chat_id or not text:
            logger.error("Chat ID and text are required to send a message.")
            return None
        return await cls.call('sendMessage', chat_id=chat_id, text=text, **kwargs)
    