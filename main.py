import logging
import signal

from common.nats_server import nc
import handlers.update

import asyncio
from anyio import run

logger = logging.getLogger()

class NATSService:
    def __init__(self):
        logger.info("Starting NATS Service")
        self.running = False

    async def start(self):
        try:
            await nc.connect()
            
            self.running = True
            logger.info("NATS Service started successfully")
            
            # Keep running
            while self.running:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Failed to start NATS service: {e}")
            raise
    
    async def stop(self):
        logger.info("Stopping NATS Service...")
        self.running = False
        await nc.close()
        logger.info("NATS Service stopped")

async def main():
    service = NATSService()

    def signal_handler():
        logger.info("Received shutdown signal")
        asyncio.create_task(service.stop())

    loop = asyncio.get_event_loop()
    loop.add_signal_handler(signal.SIGINT, signal_handler)
    loop.add_signal_handler(signal.SIGTERM, signal_handler)
    
    try:
        await service.start()
    except KeyboardInterrupt:
        await service.stop()

if __name__ == "__main__":
    run(main)