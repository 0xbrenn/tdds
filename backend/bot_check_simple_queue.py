#!/usr/bin/env python3
"""
Simple queue-based bot that works with your existing bot_check.py
"""
import os
import asyncio
import logging
import json
import time
from queue import Queue, Empty
from threading import Thread

# Import your existing bot code
from bot_check import (
    TELEGRAM_BOT_TOKEN, BACKEND_URL, FRONTEND_URL, CHANNEL_ID,
    clear_user_cache, delete_message_after_delay, decode_start_parameter,
    check_channel_membership, complete_verification, cleanup_old_pending,
    start, handle_channel_member_update, pending_verifications,
    Bot, Update, Application, CommandHandler, ChatMemberHandler
)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Simple thread-safe queue
update_queue = Queue()

async def fetcher_main():
    """Single fetcher that gets all updates"""
    logger.info("🚀 Starting Update Fetcher")
    
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    offset = None
    
    while True:
        try:
            # Get updates from Telegram
            updates = await bot.get_updates(
                offset=offset,
                timeout=30,
                allowed_updates=["message", "chat_member"]
            )
            
            if updates:
                logger.info(f"📥 Fetched {len(updates)} updates")
                
                for update in updates:
                    # Put in queue
                    update_queue.put({
                        'update_id': update.update_id,
                        'json': update.to_json()
                    })
                    offset = update.update_id + 1
                    
        except Exception as e:
            logger.error(f"Fetcher error: {e}")
            await asyncio.sleep(5)

async def worker_main():
    """Worker that processes updates"""
    worker_id = int(os.getenv("WORKER_ID", "0"))
    total_workers = int(os.getenv("TOTAL_WORKERS", "3"))
    
    logger.info(f"🔧 Starting Worker {worker_id}/{total_workers}")
    
    # Create application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Add your existing handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(ChatMemberHandler(handle_channel_member_update, ChatMemberHandler.CHAT_MEMBER))
    
    # Initialize
    await application.initialize()
    await application.start()
    
    processed = 0
    
    while True:
        try:
            # Get update from queue (with timeout)
            try:
                update_data = update_queue.get(timeout=0.5)
            except Empty:
                continue
                
            # Deserialize update
            update = Update.de_json(json.loads(update_data['json']), application.bot)
            
            # Check if this worker should handle this update
            should_process = False
            
            # For /start commands
            if update.message and update.message.text and update.message.text.startswith('/start'):
                if update.effective_user:
                    should_process = (update.effective_user.id % total_workers == worker_id)
                    
            # For channel member updates
            elif update.chat_member:
                if update.chat_member.new_chat_member:
                    user_id = update.chat_member.new_chat_member.user.id
                    should_process = (user_id % total_workers == worker_id)
            
            if should_process:
                logger.info(f"Worker {worker_id} processing update {update_data['update_id']}")
                
                # Process the update
                await application.process_update(update)
                
                processed += 1
                if processed % 10 == 0:
                    logger.info(f"Worker {worker_id} has processed {processed} updates")
                    
            else:
                # Put it back for another worker
                update_queue.put(update_data)
                await asyncio.sleep(0.1)  # Give other workers a chance
                
        except Exception as e:
            logger.error(f"Worker {worker_id} error: {e}", exc_info=True)
            await asyncio.sleep(1)

def main():
    """Main entry point"""
    mode = os.getenv("BOT_MODE", "worker")
    
    if mode == "fetcher":
        asyncio.run(fetcher_main())
    else:
        asyncio.run(worker_main())

if __name__ == '__main__':
    main()