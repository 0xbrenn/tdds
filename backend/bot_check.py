# backend/bot_check.py
import os
import asyncio
import logging
import requests
import base64
from datetime import datetime
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
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
BACKEND_URL = os.getenv("BACKEND_URL", "http://api.badge.iopn.io")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://badge.iopn.io")

if not TELEGRAM_BOT_TOKEN:
    logger.error("❌ TELEGRAM_BOT_TOKEN not found in environment variables!")
    exit(1)

bot = Bot(token=TELEGRAM_BOT_TOKEN)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command with email parameter and channel check"""
    user = update.effective_user
    user_id = user.id
    
    # Extract email and referral code from start parameter
    args = context.args
    email = None
    referral_code = None
    
    if args and args[0].startswith('verify_'):
        encoded_data = args[0].replace('verify_', '')
        try:
            import base64
            decoded_data = base64.b64decode(encoded_data).decode('utf-8')
            
            # Check if it contains referral code (email|ref format)
            if '|' in decoded_data:
                email, referral_code = decoded_data.split('|', 1)
            else:
                email = decoded_data
                
            logger.info(f"User {user_id} started with email: {email}, ref: {referral_code}")
        except:
            logger.error(f"Failed to decode data: {encoded_data}")
            email = None
    
    # Check if user is in IOPn channel
    is_channel_member = False
    CHANNEL = "@iopndiscussion"  # Your channel
    
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL, user_id=user_id)
        is_channel_member = member.status in ['member', 'administrator', 'creator']
        logger.info(f"Channel membership check: {is_channel_member} (status: {member.status})")
    except Exception as e:
        logger.error(f"Error checking channel membership: {e}")
        is_channel_member = False
    
    # Process based on membership status
    await process_user_status(update, context, user, user_id, email, referral_code, is_channel_member)

async def process_user_status(update, context, user, user_id, email, referral_code, is_channel_member):
    """Process user based on their channel membership status"""
    
    # If email provided and user is a member, link to user
    if email and is_channel_member:
        logger.info(f"Attempting to link telegram {user_id} to email {email}")
        
        # Check for duplicate Telegram account
        try:
            check_response = requests.get(f"{BACKEND_URL}/auth/telegram/verify/{user_id}")
            if check_response.ok:
                existing_data = check_response.json()
                existing_email = existing_data.get("email")
                if existing_email and existing_email != email:
                    await update.message.reply_text(
                        f"❌ This Telegram account is already linked to another email ({existing_email[:3]}***).\n\n"
                        "Each Telegram account can only be linked to one IOPn badge.\n\n"
                        "Please use a different Telegram account or contact support if you believe this is an error."
                    )
                    return
        except:
            pass  # Continue if no existing link
        
        # Update backend
        update_response = requests.post(
            f"{BACKEND_URL}/auth/telegram/link-with-channel-check",
            json={
                "email": email,
                "telegram_id": str(user_id),
                "telegram_username": user.username or "",
                "is_channel_member": is_channel_member,
                "referral_code": referral_code
            }
        )
        logger.info(f"Email link response: {update_response.status_code}")
        
        if not update_response.ok:
            logger.error(f"Link failed: {update_response.text}")
            error_data = update_response.json() if update_response.text else {}
            error_message = error_data.get("detail", "Error linking your Telegram account.")
            await update.message.reply_text(f"❌ {error_message}")
            return
    
    # Build response message
    if is_channel_member:
        response = "✅ Great! You're already a member of @iopndiscussion!\n\n"
        if email:
            response += "✨ Your Telegram task is now complete!\n\n"
            
            # Build URL with referral code if available
            return_url = FRONTEND_URL
            if referral_code:
                return_url += f"?ref={referral_code}"
            
            response += f"🌐 Return to the website to continue: {return_url}"
        else:
            response += "To complete verification, please start from the website first."
    else:
        response = (
            "👋 Welcome to IOPn Early Badge Bot!\n\n"
            "❌ You're not yet a member of our community.\n\n"
            "Please join @iopndiscussion first, then click the 'Check Again' button below.\n\n"
            "📢 Join here: https://t.me/iopndiscussion"
        )
    
    # Send inline keyboard with buttons
    keyboard = []
    
    if not is_channel_member:
        keyboard.append([InlineKeyboardButton("📢 Join IOPn Discussion", url="https://t.me/iopndiscussion")])
        # Store email and referral in callback data if available
        callback_data = f"check_membership|{email or ''}|{referral_code or ''}"
        keyboard.append([InlineKeyboardButton("🔄 Check Again", callback_data=callback_data)])
    
    # Add website button with referral code
    if email and FRONTEND_URL and not FRONTEND_URL.startswith("http://localhost"):
        button_url = FRONTEND_URL
        if referral_code:
            button_url += f"?ref={referral_code}"
        keyboard.append([InlineKeyboardButton("🌐 Back to Website", url=button_url)])
    
    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    
    # If using the production URL, add the URL to the message text as well
    if email and FRONTEND_URL.startswith("http://badge.iopn.io"):
        return_url = FRONTEND_URL
        if referral_code:
            return_url += f"?ref={referral_code}"
        response += f"\n\n🔗 Continue at: {return_url}"
    
    await update.message.reply_text(response, reply_markup=reply_markup)

async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /check command to verify badge status"""
    user_id = update.effective_user.id
    
    try:
        # Check badge status
        response = requests.get(f"{BACKEND_URL}/auth/telegram/badge/status/{user_id}")
        
        if response.status_code == 404:
            await update.message.reply_text(
                "❌ You haven't started the badge process yet.\n\n"
                "Please visit our website first to begin:\n"
                f"{FRONTEND_URL}"
            )
            return
        
        if response.ok:
            data = response.json()
            if data.get("badge_issued"):
                await update.message.reply_text(
                    "🎉 Congratulations! You've earned your Early n-Badge!\n\n"
                    f"Visit {FRONTEND_URL} to view your badge and stats."
                )
            else:
                tasks = data.get("tasks_completed", {})
                completed = sum(1 for v in tasks.values() if v)
                await update.message.reply_text(
                    f"📊 Badge Status: In Progress ({completed}/4 tasks completed)\n\n"
                    f"✅ Email: {'✅' if tasks.get('email') else '❌'}\n"
                    f"✅ Twitter: {'✅' if tasks.get('twitter') else '❌'}\n"
                    f"✅ Telegram: {'✅' if tasks.get('telegram') else '❌'}\n"
                    f"✅ Discord: {'✅' if tasks.get('discord') else '❌'}\n\n"
                    f"Complete all tasks at {FRONTEND_URL}"
                )
        else:
            await update.message.reply_text("❌ Error checking badge status. Please try again later.")
            
    except Exception as e:
        logger.error(f"Error in check command: {str(e)}")
        await update.message.reply_text("❌ An error occurred. Please try again later.")

async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries from inline keyboards"""
    query = update.callback_query
    await query.answer()
    
    # Parse callback data
    data_parts = query.data.split('|')
    action = data_parts[0]
    
    if action == "check_membership":
        email = data_parts[1] if len(data_parts) > 1 and data_parts[1] else None
        referral_code = data_parts[2] if len(data_parts) > 2 and data_parts[2] else None
        
        # Get the user who clicked the button
        user = query.from_user
        user_id = user.id
        
        # Check channel membership
        is_channel_member = False
        CHANNEL = "@iopndiscussion"
        
        try:
            member = await context.bot.get_chat_member(chat_id=CHANNEL, user_id=user_id)
            is_channel_member = member.status in ['member', 'administrator', 'creator']
            logger.info(f"Re-check membership: {is_channel_member} (status: {member.status})")
        except Exception as e:
            logger.error(f"Error checking channel membership: {e}")
            is_channel_member = False
        
        if is_channel_member and email:
            # User joined the channel! Update their status
            try:
                # Update backend
                update_response = requests.post(
                    f"{BACKEND_URL}/auth/telegram/link-with-channel-check",
                    json={
                        "email": email,
                        "telegram_id": str(user_id),
                        "telegram_username": user.username or "",
                        "is_channel_member": True,
                        "referral_code": referral_code
                    }
                )
                
                if update_response.ok:
                    # Create success keyboard
                    keyboard = []
                    if FRONTEND_URL and not FRONTEND_URL.startswith("http://localhost"):
                        button_url = FRONTEND_URL
                        if referral_code:
                            button_url += f"?ref={referral_code}"
                        keyboard.append([InlineKeyboardButton("🌐 Back to Website", url=button_url)])
                    
                    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
                    
                    success_message = (
                        "✅ Great! You've joined @iopndiscussion!\n\n"
                        "✨ Your Telegram task is now complete!\n\n"
                        "🌐 Return to the website to continue with Discord."
                    )
                    
                    if FRONTEND_URL.startswith("http://badge.iopn.io"):
                        return_url = FRONTEND_URL
                        if referral_code:
                            return_url += f"?ref={referral_code}"
                        success_message += f"\n\n🔗 Continue at: {return_url}"
                    
                    await query.edit_message_text(
                        text=success_message,
                        reply_markup=reply_markup
                    )
                else:
                    await query.edit_message_text(
                        text="❌ Error updating your status. Please try /start again."
                    )
            except Exception as e:
                logger.error(f"Error updating membership status: {e}")
                await query.edit_message_text(
                    text="❌ An error occurred. Please try /start again."
                )
        elif is_channel_member and not email:
            await query.edit_message_text(
                text="✅ You're a member of @iopndiscussion!\n\n"
                     "Please start the badge process from our website first:\n"
                     f"{FRONTEND_URL}"
            )
        else:
            # Still not a member
            keyboard = []
            keyboard.append([InlineKeyboardButton("📢 Join IOPn Discussion", url="https://t.me/iopndiscussion")])
            callback_data = f"check_membership|{email or ''}|{referral_code or ''}"
            keyboard.append([InlineKeyboardButton("🔄 Check Again", callback_data=callback_data)])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text="❌ You're not yet a member of @iopndiscussion.\n\n"
                     "Please join the channel first, then click 'Check Again'.",
                reply_markup=reply_markup
            )

if __name__ == "__main__":
    logger.info("🤖 IOPn Badge Bot is starting...")
    
    # Create application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("check", check))
    application.add_handler(CallbackQueryHandler(callback_query_handler))
    
    # Run the bot (this handles the event loop internally)
    application.run_polling(allowed_updates=Update.ALL_TYPES)