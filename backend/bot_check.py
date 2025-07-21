# Simplified version focused on verification only
import os
import asyncio
import logging
import requests
import base64
from datetime import datetime, timedelta
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup, ChatMemberUpdated
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, ChatMemberHandler
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
BACKEND_URL = os.getenv("BACKEND_URL", "https://badge.iopn.io")
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://badge.iopn.io")
CHANNEL_USERNAME = "@iopndiscussion"
CHANNEL_ID = "-1002400639662"  # Your IOPn channel ID

if not TELEGRAM_BOT_TOKEN:
    logger.error("❌ TELEGRAM_BOT_TOKEN not found in environment variables!")
    exit(1)

bot = Bot(token=TELEGRAM_BOT_TOKEN)

# Store pending verifications with auto-cleanup
pending_verifications = {}

async def delete_message_after_delay(bot, chat_id, message_id, delay_seconds):
    """Delete a message after a specified delay"""
    await asyncio.sleep(delay_seconds)
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
        logger.info(f"Deleted welcome message {message_id}")
    except Exception as e:
        logger.error(f"Failed to delete message {message_id}: {e}")

def decode_start_parameter(args):
    """Decode the start parameter to get email and referral code"""
    if not args or not args[0].startswith('verify_'):
        return None, None
    
    try:
        encoded = args[0][7:]
        encoded = encoded.replace('-', '+').replace('_', '/')
        padding = 4 - (len(encoded) % 4)
        if padding != 4:
            encoded += '=' * padding
        
        decoded = base64.b64decode(encoded).decode('utf-8')
        
        if '|' in decoded:
            email, referral_code = decoded.split('|', 1)
        else:
            email = decoded
            referral_code = None
        
        return email, referral_code
    except Exception as e:
        logger.error(f"Failed to decode start parameter: {e}")
        return None, None

async def check_channel_membership(bot, user_id):
    """Check if user is a member of the channel"""
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        is_member = member.status in ['member', 'administrator', 'creator']
        return is_member
    except Exception as e:
        logger.error(f"Error checking channel membership: {e}")
        return False

async def complete_verification(user_id, username, email, referral_code):
    """Complete the verification in the backend"""
    try:
        response = requests.post(
            f"{BACKEND_URL}/auth/telegram/link-with-channel-check",
            json={
                "email": email,
                "telegram_id": str(user_id),
                "telegram_username": username or "",
                "is_channel_member": True,
                "referral_code": referral_code
            }
        )
        return response.ok
    except Exception as e:
        logger.error(f"Error completing verification: {e}")
        return False

def cleanup_old_pending():
    """Remove pending verifications older than 1 hour"""
    if len(pending_verifications) > 50:  # Only cleanup if we have many pending
        current_time = datetime.now()
        to_remove = []
        
        for user_id, data in list(pending_verifications.items()):
            if (current_time - data['started_at']).total_seconds() > 3600:  # 1 hour
                to_remove.append(user_id)
        
        for user_id in to_remove:
            del pending_verifications[user_id]
            logger.info(f"Cleaned up old pending verification for user {user_id}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    user_id = user.id
    
    # Decode the email and referral from deep link
    email, referral_code = decode_start_parameter(context.args)
    
    if not email:
        await update.message.reply_text(
            "👋 Welcome to IOPn Early Badge Bot!\n\n"
            "Please start the verification process from our website:\n"
            f"{FRONTEND_URL}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🌐 Go to Website", url=FRONTEND_URL)
            ]])
        )
        return
    
    # Clean up old pending verifications occasionally
    cleanup_old_pending()
    
    # Check if already a member
    is_member = await check_channel_membership(context.bot, user_id)
    
    if is_member:
        # Already a member - complete immediately
        success = await complete_verification(user_id, user.username, email, referral_code)
        
        if success:
            return_url = f"{FRONTEND_URL}?ref={referral_code}" if referral_code else FRONTEND_URL
            
            await update.message.reply_text(
                "✅ Great news! You're already a member of our channel!\n\n"
                "✨ Your Telegram verification is complete!\n\n"
                "Click below to continue:",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🎯 Continue to Next Step", url=return_url)
                ]])
            )
        else:
            await update.message.reply_text(
                "❌ There was an error completing your verification.\n"
                "Please return to the website and try again."
            )
    else:
        # Not a member - store their info
        pending_verifications[user_id] = {
            'email': email,
            'username': user.username,
            'referral_code': referral_code,
            'started_at': datetime.now()
        }
        
        await update.message.reply_text(
            "👋 Welcome to IOPn Early Badge verification!\n\n"
            "📱 **Here's what to do:**\n"
            "1️⃣ Click the button below to join our channel\n"
            "2️⃣ I'll automatically detect when you join\n"
            "3️⃣ You'll receive a confirmation message\n\n"
            "🔄 I'm watching for you to join...",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📢 Join IOPn Channel", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")
            ]]),
            parse_mode='Markdown'
        )

async def handle_channel_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle when someone joins the channel - ONLY for pending verifications"""
    result = update.chat_member
    if not result:
        return
    
    # Check if this is our monitored channel
    if str(result.chat.id) != CHANNEL_ID:
        return
    
    # Get the user who joined/left
    new_member = result.new_chat_member
    old_member = result.old_chat_member
    user = new_member.user
    
    # ONLY process if we're expecting this user (in pending_verifications)
    if user.id not in pending_verifications:
        return  # Ignore - not a verification user
    
    # Check if user joined the channel
    if old_member.status in ['left', 'kicked'] and new_member.status in ['member', 'administrator', 'creator']:
        logger.info(f"Verification user {user.id} joined the channel!")
        
        verification_data = pending_verifications[user.id]
        
        # Complete their verification
        success = await complete_verification(
            user.id,
            user.username,
            verification_data['email'],
            verification_data['referral_code']
        )
        
        if success:
            # Send success message to the user
            try:
                return_url = FRONTEND_URL
                if verification_data['referral_code']:
                    return_url += f"?ref={verification_data['referral_code']}"
                
                await context.bot.send_message(
                    chat_id=user.id,
                    text=(
                        "🎉 **Awesome! You joined the channel!**\n\n"
                        "✅ Your Telegram verification is now complete!\n\n"
                        "🎯 Click below to continue:"
                    ),
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🚀 Continue to Next Step", url=return_url)
                    ]]),
                    parse_mode='Markdown'
                )
                
                # Send welcome message to channel that auto-deletes
                try:
                    welcome_msg = await context.bot.send_message(
                        chat_id=result.chat.id,
                        text=f"Welcome @{user.username or user.first_name} to IOPn! 🎉\n\nYour Early n-Badge verification is complete! ✅"
                    )
                    
                    # Schedule deletion after 15 seconds
                    asyncio.create_task(delete_message_after_delay(context.bot, result.chat.id, welcome_msg.message_id, 15))
                    
                except Exception as e:
                    logger.error(f"Error sending welcome message: {e}")
                
                # Remove from pending
                del pending_verifications[user.id]
                logger.info(f"Verification completed for user {user.id}")
                
            except Exception as e:
                logger.error(f"Error sending success message to {user.id}: {e}")
        else:
            logger.error(f"Failed to complete backend verification for user {user.id}")

def main():
    """Start the bot"""
    # Create application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    
    # Add channel member update handler
    application.add_handler(ChatMemberHandler(handle_channel_member_update, ChatMemberHandler.CHAT_MEMBER))
    
    # Start the bot
    logger.info("🚀 Starting Telegram verification bot...")
    logger.info(f"📊 Monitoring channel: {CHANNEL_ID}")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()