import os
import re
import time
import logging
from flask import Flask, request
from telebot import TeleBot

# ==================== LOGGING ====================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== ENVIRONMENT VARIABLES ====================
BOT_TOKEN = os.environ.get('BOT_TOKEN')
GROUP_ID = os.environ.get('GROUP_ID')

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN environment variable set karo!")

if not GROUP_ID:
    raise ValueError("❌ GROUP_ID environment variable set karo!")

# ==================== INIT ====================
bot = TeleBot(BOT_TOKEN)
app = Flask(__name__)
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

# ==================== TELEGRAM BOT HANDLERS ====================
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, 
        f"🤖 *Bank Alert Bot Active*\n\n"
        f"✅ Group ID: `{GROUP_ID}`\n"
        "📢 Har SMS group mein forward hoga!",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=['status'])
def status(message):
    global bot_count
    bot.reply_to(message, 
        f"✅ *Bot Status*\n"
        f"📢 Forwarding to: `{GROUP_ID}`\n"
        f"📊 Total forwarded: {bot_count}",
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda msg: True)
def forward_to_group(message):
    global bot_count
    try:
        if message.text and message.text.startswith('/'):
            return
            
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
        bot.reply_to(message, "✅ Forwarded to group!")
        
    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
        bot.reply_to(message, f"⚠️ Error: {str(e)[:100]}")

# ==================== WEBHOOK (Render.com Ke Liye) ====================
@app.route('/' + BOT_TOKEN, methods=['POST'])
def webhook():
    try:
        update = request.get_json()
        if update and 'message' in update:
            msg = update['message']
            if 'text' in msg:
                chat_id = msg['chat']['id']
                text = msg['text']
                
                # Parse and forward
                parsed = parse_sms(text)
                formatted = format_sms(text, parsed)
                
                bot.send_message(GROUP_ID, formatted, parse_mode="Markdown")
                bot.send_message(chat_id, "✅ Forwarded to group!")
        return "OK", 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return "Error", 500

@app.route('/')
def health():
    return "🤖 Bank Alert Bot is running!", 200

# ==================== SET WEBHOOK ====================
def set_webhook():
    """Render.com URL pe webhook set karo"""
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
    print(f"📢 Forwarding to Group: {GROUP_ID}")
    
    # Webhook set karo (agar URL available hai)
    render_url = os.environ.get('RENDER_URL')
    if render_url:
        set_webhook()
        print(f"🌐 Webhook mode: {render_url}")
    else:
        print("⚠️ RENDER_URL not set, using polling...")
        # Polling mode (background thread)
        import threading
        def run_polling():
            bot.infinity_polling()
        threading.Thread(target=run_polling, daemon=True).start()
    
    # Flask server (port bind)
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Server running on port {port}")
    app.run(host='0.0.0.0', port=port)