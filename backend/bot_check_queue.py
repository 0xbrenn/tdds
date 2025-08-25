#!/usr/bin/env python3
"""
Queue-based Telegram bot system
One fetcher gets updates, multiple workers process them
"""
import os
import sys
import asyncio
import logging
import json
import time
from datetime import datetime
from collections import deque
import multiprocessing

# Import everything from your existing bot
from bot_check import *

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Shared queue for updates (using Manager for cross-process sharing)
manager = multiprocessing.Manager()
update_queue = manager.Queue()
processing_times = manager.dict()

class UpdateFetcher:
    """Single instance that fetches all updates"""
    def __init__(self):
        self.bot = Bot(token=TELEGRAM_BOT_TOKEN)
        self.offset = None
        
    async def run(self):
        logger.info("🚀 Starting Update Fetcher")
        
        while True:
            try:
                # Get updates
                updates = await self.bot.get_updates(
                    offset=self.offset,
                    timeout=30,
                    allowed_updates=["message", "chat_member"]
                )
                
                if updates:
                    logger.info(f"Fetched {len(updates)} updates")
                    
                for update in updates:
                    # Put update in queue
                    update_data = {
                        'update_id': update.update_id,
                        'data': update.to_json(),
                        'timestamp': time.time()
                    }
                    update_queue.put(json.dumps(update_data))
                    
                    # Update offset
                    self.offset = update.update_id + 1
                    
            except Exception as e:
                logger.error(f"Fetcher error: {e}")
                await asyncio.sleep(5)

class UpdateWorker:
    """Worker that processes updates from queue"""
    def __init__(self, worker_id, total_workers):
        self.worker_id = worker_id
        self.total_workers = total_workers
        self.processed_count = 0
        
    async def run(self):
        logger.info(f"🔧 Starting Worker {self.worker_id}/{self.total_workers}")
        
        # Create application for this worker
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", self.wrapped_start))
        application.add_handler(ChatMemberHandler(self.wrapped_channel_update, ChatMemberHandler.CHAT_MEMBER))
        
        await application.initialize()
        await application.start()
        
        while True:
            try:
                # Get update from queue (non-blocking)
                if not update_queue.empty():
                    update_json = update_queue.get_nowait()
                    update_data = json.loads(update_json)
                    
                    # Check if this update is for this worker
                    update_id = update_data['update_id']
                    if update_id % self.total_workers == self.worker_id:
                        # Measure processing time
                        start_time = time.time()
                        
                        # Deserialize update
                        update = Update.de_json(json.loads(update_data['data']), application.bot)
                        
                        # Process update
                        await application.process_update(update)
                        
                        # Record processing time
                        processing_time = time.time() - start_time
                        processing_times[f"worker_{self.worker_id}"] = processing_time
                        
                        self.processed_count += 1
                        if self.processed_count % 10 == 0:
                            logger.info(f"Worker {self.worker_id} processed {self.processed_count} updates")
                    else:
                        # Not for this worker, put it back
                        update_queue.put(update_json)
                        
                await asyncio.sleep(0.1)  # Small delay to prevent CPU spinning
                
            except Exception as e:
                logger.error(f"Worker {self.worker_id} error: {e}")
                await asyncio.sleep(1)
    
    async def wrapped_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Wrapped start handler that checks worker assignment"""
        if update.effective_user and update.effective_user.id % self.total_workers == self.worker_id:
            logger.info(f"Worker {self.worker_id} handling /start from user {update.effective_user.id}")
            await start(update, context)
    
    async def wrapped_channel_update(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Wrapped channel update handler that checks worker assignment"""
        if update.chat_member and update.chat_member.new_chat_member:
            user_id = update.chat_member.new_chat_member.user.id
            if user_id % self.total_workers == self.worker_id:
                logger.info(f"Worker {self.worker_id} handling channel update for user {user_id}")
                await handle_channel_member_update(update, context)

async def run_fetcher():
    """Run the update fetcher"""
    fetcher = UpdateFetcher()
    await fetcher.run()

async def run_worker(worker_id, total_workers):
    """Run a worker"""
    worker = UpdateWorker(worker_id, total_workers)
    await worker.run()

async def monitor_performance():
    """Monitor and log performance metrics"""
    while True:
        await asyncio.sleep(30)
        queue_size = update_queue.qsize()
        logger.info(f"📊 Queue size: {queue_size}")
        
        for worker_id, proc_time in processing_times.items():
            logger.info(f"📊 {worker_id} last processing time: {proc_time:.2f}s")

def main():
    """Main entry point"""
    mode = os.getenv("BOT_MODE", "worker")
    worker_id = int(os.getenv("WORKER_ID", "0"))
    total_workers = int(os.getenv("TOTAL_WORKERS", "3"))
    
    if mode == "fetcher":
        logger.info("Starting in FETCHER mode")
        asyncio.run(run_fetcher())
    elif mode == "monitor":
        logger.info("Starting in MONITOR mode")
        asyncio.run(monitor_performance())
    else:
        logger.info(f"Starting in WORKER mode (ID: {worker_id})")
        asyncio.run(run_worker(worker_id, total_workers))

if __name__ == '__main__':
    main()
