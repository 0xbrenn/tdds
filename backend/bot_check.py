import os
import requests
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from dotenv import load_dotenv
import logging
import asyncio

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_USERNAME = os.getenv("TELEGRAM_CHANNEL_USERNAME", "@IOPn_io")
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

if not TELEGRAM_BOT_TOKEN:
    logger.error("❌ TELEGRAM_BOT_TOKEN not found in .env file!")
    exit(1)

bot = Bot(token=TELEGRAM_BOT_TOKEN)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command with email parameter and channel check"""
    user = update.effective_user
    user_id = user.id
    
    # Extract email from start parameter
    args = context.args
    email = None
    if args and args[0].startswith('verify_'):
        encoded_email = args[0].replace('verify_', '')
        try:
            import base64
            email = base64.b64decode(encoded_email).decode('utf-8')
            logger.info(f"User {user_id} started with email: {email}")
        except:
            logger.error(f"Failed to decode email: {encoded_email}")
            email = None
    
    # Store user data
    auth_payload = {
        "id": str(user_id),
        "username": user.username or "",
        "first_name": user.first_name or "",
        "last_name": user.last_name or "",
    }
    
    try:
        # Update backend
        response = requests.post(f"{BACKEND_URL}/auth/telegram", json=auth_payload)
        logger.info(f"Backend response: {response.status_code}")
        
        # Check if user is in IOPn channel
        is_channel_member = False
        CHANNEL = "@IOPn_io"  # Your channel
        
        try:
            member = await context.bot.get_chat_member(chat_id=CHANNEL, user_id=user_id)
            is_channel_member = member.status in ['member', 'administrator', 'creator']
            logger.info(f"Channel membership check: {is_channel_member} (status: {member.status})")
        except Exception as e:
            logger.error(f"Error checking channel membership: {e}")
            is_channel_member = False
        
        # If email provided, link to user
        if email:
            logger.info(f"Attempting to link telegram {user_id} to email {email}")
            
            # Update telegram_joined status ONLY if they're in the channel
            update_response = requests.post(
                f"{BACKEND_URL}/auth/telegram/link-with-channel-check",
                json={
                    "email": email,
                    "telegram_id": str(user_id),
                    "telegram_username": user.username or "",
                    "is_channel_member": is_channel_member
                }
            )
            logger.info(f"Email link response: {update_response.status_code}")
            
            if not update_response.ok:
                logger.error(f"Link failed: {update_response.text}")
                await update.message.reply_text(
                    "❌ Error linking your Telegram account. Please try again."
                )
                return
        else:
            logger.warning("No email provided in start parameter")
        
        # Send appropriate message based on channel membership
        if is_channel_member:
            await update.message.reply_text(
                f"✅ Perfect! You're verified AND in our channel!\n\n"
                f"• Telegram: Linked ✓\n"
                f"• Channel member: Yes ✓\n\n"
                f"Return to the website to continue."
            )
        else:
            await update.message.reply_text(
                f"⚠️ Account linked but you're not in our channel!\n\n"
                f"• Telegram: Linked ✓\n"
                f"• Channel member: No ✗\n\n"
                f"Please:\n"
                f"1. Join {CHANNEL}\n"
                f"2. Then use /check to verify membership\n\n"
                f"Join here: https://t.me/IOPn_io"
            )
        
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        import traceback
        traceback.print_exc()
        await update.message.reply_text(
            "❌ Error verifying your account. Please try again.\n"
            "If the problem persists, contact support."
        )




async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Re-check channel membership"""
    user = update.effective_user
    user_id = user.id
    
    # Check channel membership
    CHANNEL = "@IOPn_io"
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL, user_id=user_id)
        is_member = member.status in ['member', 'administrator', 'creator']
        
        if is_member:
            # Update their status
            response = requests.post(
                f"{BACKEND_URL}/auth/telegram/update-channel-status",
                json={
                    "telegram_id": str(user_id),
                    "is_channel_member": True
                }
            )
            
            await update.message.reply_text(
                "✅ Great! You're now a member of our channel!\n"
                "Return to the website to continue."
            )
        else:
            await update.message.reply_text(
                f"❌ You're still not in our channel.\n\n"
                f"Join here: https://t.me/IOPn_io\n"
                f"Then try /check again."
            )
    except Exception as e:
        await update.message.reply_text("❌ Error checking membership.")

        

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help message"""
    await update.message.reply_text(
        "🤖 IOPn Badge Bot\n\n"
        "Commands:\n"
        "/start - Verify your Telegram account\n"
        "/check - Check your verification status\n"
        "/help - Show this message\n\n"
        f"Join our channel: {TELEGRAM_CHANNEL_USERNAME}"
    )

def main():
    """Start the bot"""
    # Create application
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("check", check))
    application.add_handler(CommandHandler("help", help_command))
    
    # Start the bot
    logger.info("🤖 IOPn Badge Bot is starting...")
    logger.info(f"📢 Channel: {TELEGRAM_CHANNEL_USERNAME}")
    logger.info(f"🌐 Backend: {BACKEND_URL}")
    
    # Run the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()