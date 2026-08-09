import os
import re
import time
import logging
import threading
import random
from flask import Flask, request
from telebot import TeleBot

# ==================== LOGGING ====================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== ENVIRONMENT VARIABLES ====================
BOT_TOKEN = os.environ.get('BOT_TOKEN')

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN environment variable set karo!")

# ==================== INIT ====================
bot = TeleBot(BOT_TOKEN)
app = Flask(__name__)

GROUP_ID = os.environ.get('GROUP_ID', None)
bot_count = 0

# ==================== SMS PARSER ====================
def parse_sms(text):
    data = {
        "bank": "Unknown",
        "amount": "0",
        "txn_id": "N/A",
        "balance": "0",
        "type": "Unknown",
        "phone": "N/A"
    }
    
    phone_match = re.search(r'from\s+\(([^)]+)\)', text)
    if phone_match:
        data["phone"] = phone_match.group(1)
    
    if "Airtel Payments Bank" in text:
        data["bank"] = "Airtel Payments Bank"
    elif "Paytm" in text:
        data["bank"] = "Paytm"
    elif "PhonePe" in text:
        data["bank"] = "PhonePe"
    elif "Google Pay" in text or "GPay" in text:
        data["bank"] = "Google Pay"
    
    amount_match = re.search(r'Rs\.\s*([\d.]+)', text)
    if amount_match:
        data["amount"] = amount_match.group(1)
    
    txn_match = re.search(r'Txn ID\s*([\d]+)', text)
    if txn_match:
        data["txn_id"] = txn_match.group(1)
    
    bal_match = re.search(r'Bal[:]\s*([\d.]+)', text)
    if bal_match:
        data["balance"] = bal_match.group(1)
    
    if "debited" in text.lower():
        data["type"] = "🔴 DEBIT"
    elif "credited" in text.lower():
        data["type"] = "🟢 CREDIT"
    
    return data

def format_sms(original_text, parsed):
    return f"""
💳 *Bank Transaction Alert*

🏦 Bank: {parsed['bank']}
📊 Type: {parsed['type']}
💰 Amount: ₹{parsed['amount']}
🆔 Txn ID: `{parsed['txn_id']}`
💵 Balance: ₹{parsed['balance']}
📱 Phone: {parsed['phone']}
─────────────────
📩 *Raw SMS:*
`{original_text}`

🕐 {time.strftime('%d-%m-%Y %H:%M:%S')}
"""

# ==================== AUTO SMS SENDER (Bot Khud Bhejega) ====================
def send_auto_sms():
    """Bot khud apne aap SMS bhejega (simulate) - HAR SMS FORWARD HOGA"""
    while True:
        try:
            time.sleep(10)
            
            if not GROUP_ID:
                continue
            
            amount = round(random.uniform(0.50, 500.00), 2)
            txn_id = random.randint(100000000000, 999999999999)
            balance = round(random.uniform(10.00, 1000.00), 2)
            
            sms_text = f"SMS from (Infinix X6525): AX-AIRBNK-S\nRs. {amount} debited from Airtel Payments Bank a/c Txn ID {txn_id} Bal:{balance} Call 180023400 for help"
            
            # Bot khud ko message bhejega
            bot.send_message(
                chat_id=os.environ.get('BOT_OWNER_ID', '123456789'),
                text=sms_text
            )
            
            logger.info(f"🤖 Auto SMS sent: Rs. {amount}")
            
        except Exception as e:
            logger.error(f"Auto SMS error: {e}")
            time.sleep(30)

# ==================== BOT COMMANDS ====================
@bot.message_handler(commands=['start'])
def start(message):
    global GROUP_ID
    status = f"✅ Group set: `{GROUP_ID}`" if GROUP_ID else "❌ *No group set!* Use /addgroup -100xxxxx"
    
    bot.reply_to(message, 
        f"🤖 *Bank Alert Bot Active*\n\n"
        f"{status}\n\n"
        f"📌 *Commands:*\n"
        f"/addgroup -100xxxxx → Set group ID\n"
        f"/status → Check bot status\n"
        f"/clear → Remove group ID\n"
        f"/sendtest → Send test SMS",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=['addgroup'])
def add_group(message):
    global GROUP_ID
    try:
        args = message.text.split()
        if len(args) < 2:
            bot.reply_to(message, 
                "❌ *Usage:* `/addgroup -1004381869820`\n"
                "Group ID kahan se lein? Bot ko group mein add karo aur `/getid` bhejo.",
                parse_mode="Markdown"
            )
            return
        
        new_group_id = args[1].strip()
        
        if not new_group_id.startswith('-'):
            bot.reply_to(message, "❌ Group ID `-100xxxxx` format mein hona chahiye!", parse_mode="Markdown")
            return
        
        GROUP_ID = new_group_id
        bot.reply_to(message, 
            f"✅ *Group ID set!*\n"
            f"📢 Forwarding to: `{GROUP_ID}`\n\n"
            f"Ab jo bhi SMS aayega, is group mein forward hoga!",
            parse_mode="Markdown"
        )
        
        logger.info(f"✅ Group ID changed to: {GROUP_ID}")
        
    except Exception as e:
        bot.reply_to(message, f"⚠️ Error: {str(e)[:100]}")

@bot.message_handler(commands=['getid'])
def get_id(message):
    chat_id = message.chat.id
    chat_type = "Group" if chat_id < 0 else "Private"
    bot.reply_to(message, 
        f"📌 *Chat Info*\n"
        f"🆔 Chat ID: `{chat_id}`\n"
        f"📊 Type: {chat_type}\n\n"
        f"Group ID copy karo: `/addgroup {chat_id}`",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=['status'])
def status(message):
    global GROUP_ID, bot_count
    group_status = f"`{GROUP_ID}`" if GROUP_ID else "❌ *Not set*"
    
    bot.reply_to(message, 
        f"✅ *Bot Status*\n"
        f"📢 Group: {group_status}\n"
        f"📊 Forwarded: {bot_count} messages\n"
        f"🤖 Bot: @{bot.get_me().username}",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=['clear'])
def clear_group(message):
    global GROUP_ID
    GROUP_ID = None
    bot.reply_to(message, "🗑️ *Group ID cleared!*\nUse `/addgroup -100xxxxx` to set new.", parse_mode="Markdown")

@bot.message_handler(commands=['sendtest'])
def send_test(message):
    """Test SMS bhejne ke liye"""
    test_sms = f"SMS from (Infinix X6525): AX-AIRBNK-S\nRs. 100.00 debited from Airtel Payments Bank a/c Txn ID 123456789012 Bal:500.00 Call 180023400 for help"
    # Bot khud ko message bhejega
    bot.send_message(
        chat_id=message.chat.id,
        text=test_sms
    )
    bot.reply_to(message, "📤 Test SMS sent! Check group for forward.")

# ==================== FORWARD SMS (Har SMS Forward Hoga) ====================
@bot.message_handler(func=lambda msg: True)
def forward_to_group(message):
    global GROUP_ID, bot_count
    
    # Skip commands
    if message.text and message.text.startswith('/'):
        return
    
    # Check if group is set
    if not GROUP_ID:
        bot.reply_to(message, 
            "❌ *Group ID not set!*\n"
            "Use `/addgroup -100xxxxx` to set group ID.",
            parse_mode="Markdown"
        )
        return
    
    try:
        logger.info(f"📩 Received SMS: {message.text[:50]}...")
        
        original_text = message.text
        parsed = parse_sms(original_text)
        formatted = format_sms(original_text, parsed)
        
        # Group mein send
        sent = bot.send_message(
            GROUP_ID,
            formatted,
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
        
        bot_count += 1
        logger.info(f"✅ Forwarded! Msg ID: {sent.message_id}")
        
        # User ko confirm
        bot.reply_to(message, f"✅ Forwarded to group `{GROUP_ID}`", parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
        
        if "Forbidden" in str(e) or "chat not found" in str(e):
            bot.reply_to(message, 
                f"❌ *Group not found!*\n"
                f"Bot ko group mein add karo aur admin banao.\n"
                f"Group ID: `{GROUP_ID}`",
                parse_mode="Markdown"
            )
        else:
            bot.reply_to(message, f"⚠️ Error: {str(e)[:100]}")

# ==================== WEBHOOK ====================
@app.route('/' + BOT_TOKEN, methods=['POST'])
def webhook():
    try:
        update = request.get_json()
        if update and 'message' in update:
            msg = update['message']
            if 'text' in msg:
                text = msg['text']
                
                if GROUP_ID:
                    parsed = parse_sms(text)
                    formatted = format_sms(text, parsed)
                    bot.send_message(GROUP_ID, formatted, parse_mode="Markdown")
        return "OK", 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return "Error", 500

@app.route('/')
def health():
    return "🤖 Bank Alert Bot is running!", 200

# ==================== SET WEBHOOK ====================
def set_webhook():
    render_url = os.environ.get('RENDER_URL')
    if render_url:
        webhook_url = f"{render_url}/{BOT_TOKEN}"
        try:
            bot.remove_webhook()
            bot.set_webhook(url=webhook_url)
            logger.info(f"✅ Webhook set: {webhook_url}")
            return True
        except Exception as e:
            logger.error(f"❌ Webhook set failed: {e}")
            return False
    return False

# ==================== MAIN ====================
if __name__ == "__main__":
    print("🤖 Bank Alert Bot Started!")
    print(f"📢 Current Group: {GROUP_ID if GROUP_ID else 'Not set'}")
    print("📌 Commands: /addgroup, /getid, /status, /clear, /sendtest")
    
    # Auto SMS sender
    auto_sms_thread = threading.Thread(target=send_auto_sms, daemon=True)
    auto_sms_thread.start()
    print("🔄 Auto SMS sender started (10 seconds interval)")
    
    render_url = os.environ.get('RENDER_URL')
    if render_url:
        set_webhook()
        print(f"🌐 Webhook mode: {render_url}")
    else:
        print("⚠️ RENDER_URL not set, using polling...")
        def run_polling():
            bot.infinity_polling()
        threading.Thread(target=run_polling, daemon=True).start()
    
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Server running on port {port}")
    app.run(host='0.0.0.0', port=port)