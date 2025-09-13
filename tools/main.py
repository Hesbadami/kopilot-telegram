import logging
from typing import List, Dict, Any
from common.mysql import MySQL as db

import anyio

logger = logging.getLogger()

class TelegramHandler:

    @classmethod
    async def collect_updates(cls) -> List[Dict[Any, Any]]:

        query = """
        SELECT 
            id,
            

        FROM `raw_events`
        WHERE `source` = 'telegram'
        AND `processed` = FALSE
        LIMIT 1000
        """

        ...