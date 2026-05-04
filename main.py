import os
from dotenv import load_dotenv
import telebot
import subprocess
import json
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from utils.wisun_network import WisunNetwork

# Load environment variables from .env file
load_dotenv()

# Minimal test bot to verify your Telegram bot token and basic handlers.
# Usage: set TELEGRAM_BOT_TOKEN in .env file or as environment variable

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Initialize WiSUN network manager
wisun = WisunNetwork()

# Basic validation: a real bot token contains a ':' separating id and hash
if TOKEN.startswith("<") or ":" not in TOKEN:
    print("ERROR: set TELEGRAM_BOT_TOKEN env var or paste token into the file.")
    print("See README.md for examples.")
    raise SystemExit(1)

bot = telebot.TeleBot(TOKEN, parse_mode='HTML')

# Store user selected IPs for CoAP commands
user_selected_ip = {}

# Load CoAP endpoints from JSON config
def load_coap_endpoints():
    """Load CoAP endpoints from JSON configuration file"""
    try:
        with open('config/coap_endpoints.json', 'r') as f:
            data = json.load(f)
            return data.get('coap_endpoints', [])
    except Exception as e:
        print(f"Error loading CoAP endpoints: {e}")
        return []

COAP_ENDPOINTS = load_coap_endpoints()

# Build command menu dynamically from endpoints
def build_command_menu():
    """Build command menu with essential commands only"""
    commands = [
        BotCommand("start", "Get started"),
        BotCommand("ip", "Select connected node IP"),
        BotCommand("coap", "Query CoAP endpoints"),
        BotCommand("connected_nodes", "Show connected nodes"),
        BotCommand("not_connected_nodes", "Show disconnected nodes"),
    ]
    
    return commands

# Set command menu
bot.set_my_commands(build_command_menu())

def print_getme():
    try:
        me = bot.get_me()
        print("Bot info:", me)
    except Exception as e:
        print("getMe failed:", e)


@bot.message_handler(commands=['start'])
def handle_start(msg):
    bot.reply_to(msg, "Bot is working ✅\nYour id: {}".format(msg.from_user.id))


@bot.message_handler(commands=['help'])
def handle_help(msg):
    """Show all available commands as inline keyboard buttons"""
    markup = InlineKeyboardMarkup()
    
    # Add buttons row by row
    markup.add(InlineKeyboardButton("Start", callback_data="cmd_start"))
    markup.add(InlineKeyboardButton("Connected Nodes", callback_data="cmd_connected"))
    markup.add(InlineKeyboardButton("Not Connected Nodes", callback_data="cmd_disconnected"))
    markup.add(InlineKeyboardButton("Detail", callback_data="cmd_detail"))
    markup.add(InlineKeyboardButton("Pole", callback_data="cmd_pole"))
    markup.add(InlineKeyboardButton("Border Router", callback_data="cmd_br"))
    
    bot.send_message(msg.chat.id, "Available Commands:", reply_markup=markup)


@bot.message_handler(commands=['ip'])
def handle_ip(msg):
    """Show connected nodes as IP selector (3 columns, last 4 digits)"""
    try:
        connected, _, _ = wisun.get_connected_nodes()
        
        if not connected:
            bot.reply_to(msg, "No connected nodes available.")
            return
        
        markup = InlineKeyboardMarkup()
        
        # Add buttons in 3 columns
        row = []
        for node_name, ip in connected:
            last_4_digits = ip[-4:]
            row.append(InlineKeyboardButton(last_4_digits, callback_data=f"ip_{ip}"))
            
            if len(row) == 3:
                markup.add(*row)
                row = []
        
        # Add remaining buttons
        if row:
            markup.add(*row)
        
        bot.send_message(msg.chat.id, f"<b>Select IP ({len(connected)} connected)</b>", reply_markup=markup, parse_mode='HTML')
    except Exception as e:
        bot.reply_to(msg, f"Error retrieving connected nodes: {e}")


@bot.message_handler(commands=['ping'])
def handle_ping(msg):
    bot.reply_to(msg, "pong")


@bot.message_handler(commands=['connected_nodes'])
def handle_connected_nodes(msg):
    """Show only connected WiSUN network nodes"""
    try:
        report = wisun.format_connected_nodes()
        bot.send_message(msg.chat.id, report, parse_mode='HTML')
    except Exception as e:
        bot.reply_to(msg, f"Error retrieving connected nodes: {e}")


@bot.message_handler(commands=['disconnected_nodes', 'not_connected_nodes'])
def handle_disconnected_nodes(msg):
    """Show only disconnected WiSUN network nodes"""
    try:
        report = wisun.format_disconnected_nodes()
        bot.send_message(msg.chat.id, report, parse_mode='HTML')
    except Exception as e:
        bot.reply_to(msg, f"Error retrieving disconnected nodes: {e}")


@bot.message_handler(commands=['detail'])
def handle_detail(msg):
    """Show details of pole"""
    bot.reply_to(msg, "Pole details (implementation pending)")


@bot.message_handler(commands=['pole'])
def handle_pole(msg):
    """Control the pole"""
    bot.reply_to(msg, "Pole control (implementation pending)")


@bot.message_handler(commands=['br'])
def handle_br(msg):
    """Border Router control & status"""
    bot.reply_to(msg, "Border Router status (implementation pending)")


@bot.message_handler(commands=['coap'])
def handle_coap(msg):
    """Show available CoAP endpoints in 3-column grid"""
    user_id = msg.from_user.id
    
    if user_id not in user_selected_ip:
        bot.reply_to(msg, "Please select an IP first using /ip command")
        return
    
    selected_ip = user_selected_ip[user_id]
    markup = InlineKeyboardMarkup()
    
    # Add CoAP endpoint buttons in 3 columns
    row = []
    for endpoint in COAP_ENDPOINTS:
        row.append(InlineKeyboardButton(endpoint['name'], callback_data=f"coap_{endpoint['endpoint']}"))
        
        if len(row) == 3:
            markup.add(*row)
            row = []
    
    # Add remaining buttons
    if row:
        markup.add(*row)
    
    bot.send_message(msg.chat.id, f"<b>CoAP Endpoints for {selected_ip}</b>\n\nSelect endpoint:", reply_markup=markup, parse_mode='HTML')


@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    """Handle inline button clicks"""
    user_id = call.from_user.id
    
    # Handle IP selection
    if call.data.startswith("ip_"):
        selected_ip = call.data[3:]  # Remove "ip_" prefix
        user_selected_ip[user_id] = selected_ip
        bot.send_message(call.message.chat.id, f"✅ Selected IP: <b>{selected_ip}</b>\n\nNow use /coap to query endpoints", parse_mode='HTML')
        bot.answer_callback_query(call.id, "IP selected!")
        return
    
    # Handle CoAP endpoint queries
    if call.data.startswith("coap_"):
        if user_id not in user_selected_ip:
            bot.send_message(call.message.chat.id, "No IP selected. Use /ip first.")
            bot.answer_callback_query(call.id)
            return
        
        endpoint_path = call.data[5:]  # Remove "coap_" prefix to get endpoint path
        selected_ip = user_selected_ip[user_id]
        
        # Find endpoint name for display
        endpoint_name = endpoint_path
        for ep in COAP_ENDPOINTS:
            if ep['endpoint'] == endpoint_path:
                endpoint_name = ep['name']
                break
        
        # Execute CoAP command
        coap_url = f"coap://[{selected_ip}]:5683{endpoint_path}"
        cmd = f"coap-client-notls -m get {coap_url}"
        
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            response = result.stdout if result.stdout else result.stderr
            
            if not response:
                response = "No response from endpoint"
            
            # Send response back to bot
            bot.send_message(call.message.chat.id, f"<b>CoAP Response: {endpoint_name}</b>\n\n<code>{response}</code>", parse_mode='HTML')
        except subprocess.TimeoutExpired:
            bot.send_message(call.message.chat.id, f"❌ Timeout: CoAP request to {endpoint_name} took too long")
        except Exception as e:
            bot.send_message(call.message.chat.id, f"❌ Error: {e}")
        
        bot.answer_callback_query(call.id)
        return
    
    # Handle other commands
    if call.data == "cmd_start":
        bot.send_message(call.message.chat.id, "Bot is working ✅\nYour id: {}".format(call.from_user.id))
    elif call.data == "cmd_connected":
        try:
            report = wisun.format_connected_nodes()
            bot.send_message(call.message.chat.id, report, parse_mode='HTML')
        except Exception as e:
            bot.send_message(call.message.chat.id, f"Error: {e}")
    elif call.data == "cmd_disconnected":
        try:
            report = wisun.format_disconnected_nodes()
            bot.send_message(call.message.chat.id, report, parse_mode='HTML')
        except Exception as e:
            bot.send_message(call.message.chat.id, f"Error: {e}")
    elif call.data == "cmd_detail":
        bot.send_message(call.message.chat.id, "Pole details (implementation pending)")
    elif call.data == "cmd_pole":
        bot.send_message(call.message.chat.id, "Pole control (implementation pending)")
    elif call.data == "cmd_br":
        bot.send_message(call.message.chat.id, "Border Router status (implementation pending)")
    
    # Answer callback query to remove loading state
    bot.answer_callback_query(call.id)


@bot.message_handler(func=lambda m: True)
def handle_all(msg):
    # Minimal behavior: echo incoming text back to the sender
    bot.reply_to(msg, "Echo: " + (msg.text or "(no text)"))


if __name__ == '__main__':
    print_getme()
    print("Starting polling. Press Ctrl+C to stop.")
    try:
        bot.infinity_polling(timeout=20, long_polling_timeout=5)
    except KeyboardInterrupt:
        print("Stopped by user.")