import logging
import sqlite3  # This is built-in, no need to install!
import hashlib
import secrets
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Configuration - REPLACE WITH YOUR ACTUAL VALUES
BOT_TOKEN = "8217422409:AAH-AowNOblpvlRMm76ds6NcUlCFp8GSyWw"  # Get from @BotFather
ADMIN_IDS = [7929255261]  # Your user ID
TELE_BIRR_ACCOUNT = "0901430487"
PREMIUM_PRICE = "50 ETB"

class ElitePaymentBot:
    def __init__(self):
        self.db_connection = sqlite3.connect('premium_payments.db', check_same_thread=False)
        self.init_database()
    
    def init_database(self):
        cursor = self.db_connection.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                first_name TEXT,
                amount REAL,
                status TEXT DEFAULT 'pending',
                verification_code TEXT UNIQUE,
                admin_approved INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.db_connection.commit()
        logging.info("Database initialized successfully")

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.message.from_user
        welcome_text = f"""
🤖 **ELITE PREMIUM BOT** 🚀

Welcome *{user.first_name}*! 

✨ **Premium Features:**
• Advanced AI Processing
• Priority Support
• Exclusive Content
• Faster Responses

💳 **Premium Subscription:** {PREMIUM_PRICE}
        """
        
        keyboard = [
            [InlineKeyboardButton("💎 Buy Premium", callback_data="buy_premium")],
            [InlineKeyboardButton("📋 My Status", callback_data="check_status")],
            [InlineKeyboardButton("🛟 Support", callback_data="support")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        if query.data == "buy_premium":
            await self.show_payment_instructions(query)
        elif query.data == "check_status":
            await self.check_payment_status(query)
        elif query.data == "support":
            await self.show_support(query)

    async def show_payment_instructions(self, query):
        payment_text = f"""
💎 **PREMIUM SUBSCRIPTION**

💰 **Price:** {PREMIUM_PRICE}
📱 **Tele Birr:** `{TELE_BIRR_ACCOUNT}`
        
📋 **Payment Instructions:**
1. Open Tele Birr App
2. Send {PREMIUM_PRICE} to the number above
3. Take **screenshot** of payment confirmation
4. Send the screenshot here
        
✅ **Verification Process:**
- Automated system check
- Admin manual verification
- Usually 2-5 minutes
- You'll receive verification code
        
🛡️ *100% Secure & Guaranteed*
        """
        
        await query.edit_message_text(
            payment_text,
            parse_mode='Markdown'
        )

    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.message.from_user
        
        # Generate unique verification code
        verification_code = secrets.token_hex(4).upper()
        
        try:
            cursor = self.db_connection.cursor()
            cursor.execute('''
                INSERT INTO payments (user_id, username, first_name, verification_code, status)
                VALUES (?, ?, ?, ?, ?)
            ''', (user.id, user.username, user.first_name, verification_code, 'under_review'))
            self.db_connection.commit()
            
            # Notify admin
            await self.notify_admins(context, user, verification_code)
            
            success_message = f"""
✅ **Payment Proof Received!**

👤 User: {user.first_name}
📧 Username: @{user.username if user.username else 'N/A'}
🆔 User ID: `{user.id}`
🔐 Verification Code: `{verification_code}`
⏱️ Status: *Under Review*
            
📋 **Next Steps:**
1. Admin will verify manually
2. You'll be notified when approved
3. Use code to activate premium
            
⏳ Estimated time: 2-5 minutes
            """
            
            await update.message.reply_text(
                success_message,
                parse_mode='Markdown'
            )
            
        except sqlite3.IntegrityError:
            await update.message.reply_text("❌ Error: Please try sending your payment proof again.")
        except Exception as e:
            logging.error(f"Database error: {e}")
            await update.message.reply_text("❌ System error. Please contact support.")

    async def notify_admins(self, context, user, verification_code):
        admin_message = f"""
🚨 **NEW PAYMENT VERIFICATION REQUIRED**

👤 User: {user.first_name} (@{user.username})
🆔 ID: `{user.id}`
🔐 Code: `{verification_code}`
⏰ Time: {datetime.now().strftime('%H:%M:%S')}
        
✅ Use: `/verify {verification_code}` to approve
❌ Use: `/reject {verification_code}` to reject
        """
        
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=admin_message,
                    parse_mode='Markdown'
                )
            except Exception as e:
                logging.error(f"Failed to notify admin {admin_id}: {e}")

    async def verify_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.message.from_user
        
        if user.id not in ADMIN_IDS:
            await update.message.reply_text("❌ Admin access required.")
            return
        
        if not context.args:
            await update.message.reply_text("❌ Usage: /verify <verification_code>")
            return
        
        verification_code = context.args[0].upper()
        
        try:
            cursor = self.db_connection.cursor()
            cursor.execute('''
                UPDATE payments SET status = 'approved', admin_approved = 1 
                WHERE verification_code = ? AND status = 'under_review'
            ''', (verification_code,))
            
            if cursor.rowcount > 0:
                self.db_connection.commit()
                
                # Get user details
                cursor.execute('SELECT user_id FROM payments WHERE verification_code = ?', (verification_code,))
                result = cursor.fetchone()
                
                if result:
                    user_id = result[0]
                    success_message = """
🎉 **PREMIUM ACTIVATED!**

✅ Your payment has been verified!
🔓 Premium features are now unlocked

✨ **Thank you for upgrading!**
                    """
                    
                    try:
                        await context.bot.send_message(
                            chat_id=user_id,
                            text=success_message,
                            parse_mode='Markdown'
                        )
                    except Exception as e:
                        logging.error(f"Failed to notify user {user_id}: {e}")
                
                await update.message.reply_text(f"✅ Payment {verification_code} verified successfully!")
            else:
                await update.message.reply_text("❌ Invalid or already processed verification code.")
                
        except Exception as e:
            logging.error(f"Verification error: {e}")
            await update.message.reply_text("❌ Database error during verification.")

    async def check_payment_status(self, query):
        user = query.from_user
        
        cursor = self.db_connection.cursor()
        cursor.execute('''
            SELECT status, verification_code, created_at 
            FROM payments 
            WHERE user_id = ? 
            ORDER BY created_at DESC 
            LIMIT 1
        ''', (user.id,))
        
        result = cursor.fetchone()
        
        if result:
            status, code, created_at = result
            status_message = f"""
📋 **Payment Status**

🔐 Code: `{code}`
📊 Status: *{status.upper()}*
🕐 Submitted: {created_at}
            """
        else:
            status_message = "❌ No payment records found."
        
        await query.edit_message_text(
            status_message,
            parse_mode='Markdown'
        )

    async def show_support(self, query):
        support_text = """
🛟 **Support**

For any issues with payment verification:
• Double-check your screenshot is clear
• Ensure payment was sent to correct number
• Keep your verification code safe
        
📞 Contact admin for help.
        """
        await query.edit_message_text(support_text)

def main():
    if BOT_TOKEN == "YOUR_NEW_BOT_TOKEN_HERE":
        print("❌ ERROR: Please set your actual BOT_TOKEN in the code!")
        return
    
    try:
        application = Application.builder().token(BOT_TOKEN).build()
        bot = ElitePaymentBot()
        
        # Add handlers
        application.add_handler(CommandHandler("start", bot.start_command))
        application.add_handler(CommandHandler("verify", bot.verify_command))
        application.add_handler(CallbackQueryHandler(bot.button_handler))
        application.add_handler(MessageHandler(filters.PHOTO, bot.handle_photo))
        
        print("🤖 Elite Payment Bot Started Successfully!")
        print("📱 Listening for messages...")
        
        application.run_polling()
        
    except Exception as e:
        logging.error(f"Bot failed to start: {e}")

if __name__ == '__main__':
    main()