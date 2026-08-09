import os
import re
import time
from telebot import TeleBot, types

# ==================== ENVIRONMENT VARIABLES ====================
BOT_TOKEN = os.environ.get('BOT_TOKEN')
GROUP_ID = os.environ.get('GROUP_ID')

# Agar token set nahi hai toh error
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN environment variable set karo!\n\nExport: export BOT_TOKEN='your_token'")

if not GROUP_ID:
    raise ValueError("❌ GROUP_ID environment variable set karo!\n\nExport: export GROUP_ID='-1001234567890'")

bot = TeleBot(BOT_TOKEN)

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
    
    # Phone number
    phone_match = re.search(r'from\s+\(([^)]+)\)', text)
    if phone_match:
        data["phone"] = phone_match.group(1)
    
    # Bank
    if "Airtel Payments Bank" in text:
        data["bank"] = "Airtel Payments Bank"
    elif "Paytm" in text:
        data["bank"] = "Paytm"
    elif "PhonePe" in text:
        data["bank"] = "PhonePe"
    elif "Google Pay" in text or "GPay" in text:
        data["bank"] = "Google Pay"
    
    # Amount
    amount_match = re.search(r'Rs\.\s*([\d.]+)', text)
    if amount_match:
        data["amount"] = amount_match.group(1)
    
    # Txn ID
    txn_match = re.search(r'Txn ID\s*([\d]+)', text)
    if txn_match:
        data["txn_id"] = txn_match.group(1)
    
    # Balance
    bal_match = re.search(r'Bal[:]\s*([\d.]+)', text)
    if bal_match:
        data["balance"] = bal_match.group(1)
    
    # Type
    if "debited" in text.lower():
        data["type"] = "🔴 DEBIT"
    elif "credited" in text.lower():
        data["type"] = "🟢 CREDIT"
    
    return data

# ==================== FORMAT ====================
def format_sms(original_text, parsed):
    formatted = f"""
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
    return formatted

# ==================== BOT COMMANDS ====================
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, 
        "🤖 *Bank Alert Bot Active*\n\n"
        f"✅ Group ID: `{GROUP_ID}`\n"
        "📢 Har SMS group mein forward hoga!",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=['status'])
def status(message):
    bot.reply_to(message, 
        f"✅ *Bot Status*\n"
        f"📢 Forwarding to: `{GROUP_ID}`\n"
        f"📊 Total forwarded: {getattr(bot, 'count', 0)}",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=['setgroup'])
def set_group(message):
    """Group ID change (temporary)"""
    global GROUP_ID
    try:
        args = message.text.split()
        if len(args) < 2:
            bot.reply_to(message, "❌ Usage: /setgroup -1001234567890")
            return
        GROUP_ID = args[1]
        bot.reply_to(message, f"✅ Group updated: `{GROUP_ID}`", parse_mode="Markdown")
    except:
        bot.reply_to(message, "❌ Error! Try: /setgroup -1001234567890")

# ==================== FORWARD SMS ====================
@bot.message_handler(func=lambda msg: True)
def forward_to_group(message):
    try:
        original_text = message.text
        parsed = parse_sms(original_text)
        formatted = format_sms(original_text, parsed)
        
        bot.send_message(GROUP_ID, formatted, parse_mode="Markdown")
        bot.count = getattr(bot, 'count', 0) + 1
        bot.reply_to(message, "✅ Forwarded to group!")
        
    except Exception as e:
        bot.reply_to(message, f"⚠️ Error: {str(e)[:100]}")

# ==================== MAIN ====================
if __name__ == "__main__":
    print("🤖 Bank Alert Bot Started!")
    print(f"📢 Forwarding to Group: {GROUP_ID}")
    print("Press Ctrl+C to stop\n")
    bot.infinity_polling()