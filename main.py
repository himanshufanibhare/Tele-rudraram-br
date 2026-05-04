import os
from dotenv import load_dotenv
import telebot
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

# Set command menu
bot.set_my_commands([
    BotCommand("start", "Get started"),
    BotCommand("help", "Show all commands"),
    BotCommand("connected_nodes", "Show connected nodes"),
    BotCommand("not_connected_nodes", "Show disconnected nodes"),
    BotCommand("detail", "Show details of pole"),
    BotCommand("pole", "Control the pole"),
    BotCommand("br", "Border Router control & status"),
])

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


@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    """Handle inline button clicks"""
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