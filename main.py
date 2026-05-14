import os
from dotenv import load_dotenv
import telebot
import subprocess
import json
import re
import shutil
import html
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from utils.wisun_network import WisunNetwork
from utils.helpers import reboot_system

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
monitor_message_state = {}

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


def run_linux_command(command, timeout=3):
    """Run a shell command safely and return (ok, output_or_error)."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        err = (result.stderr or result.stdout).strip()
        return False, err or "Command failed"
    except subprocess.TimeoutExpired:
        return False, "Command timeout"
    except Exception as e:
        return False, str(e)


def get_cpu_temp():
    """Read CPU temperature via vcgencmd."""
    if not shutil.which("vcgencmd"):
        return "N/A (vcgencmd missing)"

    ok, output = run_linux_command("vcgencmd measure_temp")
    if not ok:
        return f"N/A ({output})"

    match = re.search(r"temp=([0-9.]+)'C", output)
    if match:
        return f"{match.group(1)}°C"

    return "N/A (temperature unavailable)"


def get_cpu_usage():
    """Read current CPU usage percentage."""
    ok, output = run_linux_command(
        "top -bn2 | grep \"Cpu(s)\" | tail -n1 | awk '{printf(\"%.1f%%\\n\", 100 - $8)}'",
        timeout=8,
    )
    if ok and output:
        return output

    # Fallback parser for top variants where idle column is not at fixed field index.
    ok, output = run_linux_command(
        "top -bn2 | grep \"Cpu(s)\" | tail -n1 | awk -F',' '{for(i=1;i<=NF;i++){if($i ~ / id/){gsub(/[^0-9.]/,\"\",$i); if($i!=\"\"){printf(\"%.1f%%\", 100 - $i); exit}}}}'",
        timeout=8,
    )
    if ok and output:
        return output
    return "N/A"


def get_ram_usage():
    """Read RAM usage from free -m."""
    ok, output = run_linux_command("free -m")
    if not ok:
        return "N/A"

    for line in output.splitlines():
        if line.lower().startswith("mem:"):
            parts = line.split()
            if len(parts) >= 3:
                total = int(parts[1])
                used = int(parts[2])
                pct = (used / total) * 100 if total else 0
                return f"{used}MB/{total}MB ({pct:.1f}%)"

    return "N/A"


def get_disk_usage():
    """Read root filesystem usage."""
    ok, output = run_linux_command("df -h /")
    if not ok:
        return "N/A"

    lines = output.splitlines()
    if len(lines) >= 2:
        parts = lines[1].split()
        if len(parts) >= 5:
            size = parts[1]
            used = parts[2]
            pct = parts[4]
            return f"{used}/{size} ({pct})"

    return "N/A"


def get_uptime():
    """Read uptime in human-readable format."""
    ok, output = run_linux_command("uptime -p")
    if ok and output:
        return output.replace("up ", "", 1)
    return "N/A"


def get_ip_address():
    """Get primary IPv4 address."""
    ok, output = run_linux_command("hostname -I | awk '{print $1}'")
    if ok and output:
        return output
    return "N/A"


def get_active_network_interface():
    """Get currently active default-route network interface."""
    ok, output = run_linux_command("ip route get 8.8.8.8 | awk '{for(i=1;i<=NF;i++) if($i==\"dev\"){print $(i+1); exit}}'")
    if ok and output:
        return output.splitlines()[0].strip()

    ok, output = run_linux_command("ip route | grep default | awk '{print $5}'")
    if ok and output:
        return output.splitlines()[0].strip()

    return "unknown"


def get_wifi_status():
    """Get WiFi SSID from iwgetid."""
    active_interface = get_active_network_interface()

    ok, output = run_linux_command("iwgetid -r")
    if "not found" in output.lower():
        return "N/A (iwgetid missing)"

    if active_interface.startswith("wlan"):
        if ok and output:
            return f"{output} ({active_interface})"
        return f"N/A ({active_interface})"

    if active_interface and active_interface != "unknown":
        return f"N/A ({active_interface})"

    if ok and output:
        return f"{output} (wlan0)"

    return "N/A (unknown)"


def get_monitor_text():
    """Build the monitor dashboard message text."""
    ip_address = get_ip_address()
    cpu_temp = get_cpu_temp()
    cpu_usage = get_cpu_usage()
    ram_usage = get_ram_usage()
    disk_usage = get_disk_usage()
    uptime = get_uptime()
    wifi_name = get_wifi_status()

    ip_address = html.escape(ip_address)
    cpu_temp = html.escape(cpu_temp)
    cpu_usage = html.escape(cpu_usage)
    ram_usage = html.escape(ram_usage)
    disk_usage = html.escape(disk_usage)
    uptime = html.escape(uptime)
    wifi_name = html.escape(wifi_name)

    return (
        "<b>🖥 Raspberry Pi Monitor</b>\n\n"
        "<pre>"
        f"IP        : {ip_address}\n"
        f"CPU Temp  : {cpu_temp}\n"
        f"CPU Usage : {cpu_usage}\n"
        f"RAM Usage : {ram_usage}\n"
        f"Disk Usage: {disk_usage}\n"
        f"Uptime    : {uptime}\n"
            f"Network   : {wifi_name}"
        "</pre>"
    )


def monitor_keyboard():
    """Inline keyboard for monitor dashboard actions."""
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔄 Refresh", callback_data="monitor_refresh"))
    return markup


def show_monitor_dashboard(chat_id, user_id, message_id=None):
    """Render or refresh monitor dashboard in a single message."""
    text = get_monitor_text()
    reply_markup = monitor_keyboard()
    key = (user_id, chat_id)

    if message_id:
        bot.edit_message_text(
            text,
            chat_id,
            message_id,
            reply_markup=reply_markup,
            parse_mode='HTML',
        )
        monitor_message_state[key] = message_id
        return message_id

    sent = bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode='HTML')
    monitor_message_state[key] = sent.message_id
    return sent.message_id


def build_ip_selection_keyboard(callback_prefix):
    """Build a 3-column keyboard for connected WiSUN IPv6 nodes."""
    connected, _, _ = wisun.get_connected_nodes()

    if not connected:
        return None

    markup = InlineKeyboardMarkup()
    row = []

    for node_name, ip in connected:
        last_4_digits = ip[-4:]
        row.append(InlineKeyboardButton(last_4_digits, callback_data=f"{callback_prefix}{ip}"))

        if len(row) == 3:
            markup.add(*row)
            row = []

    if row:
        markup.add(*row)

    return markup


def build_status_coap_keyboard(back_callback="status_back_to_ips"):
    """Keyboard for CoAP endpoint selection inside /status."""
    markup = InlineKeyboardMarkup()
    row = []

    for endpoint in COAP_ENDPOINTS:
        row.append(InlineKeyboardButton(endpoint['name'], callback_data=f"coap_{endpoint['endpoint']}"))

        if len(row) == 3:
            markup.add(*row)
            row = []

    if row:
        markup.add(*row)

    markup.add(InlineKeyboardButton("Back", callback_data=back_callback))
    return markup


def show_status_ip_menu(chat_id, message_id=None):
    """Display the /status IP selector menu."""
    markup = build_ip_selection_keyboard("status_ip_")

    if not markup:
        text = "No connected nodes available."
        if message_id:
            bot.edit_message_text(text, chat_id, message_id)
        else:
            bot.send_message(chat_id, text)
        return False

    text = "<b>Select IP for status</b>\n\nChoose a connected IPv6 node:"
    if message_id:
        bot.edit_message_text(text, chat_id, message_id, reply_markup=markup, parse_mode='HTML')
    else:
        bot.send_message(chat_id, text, reply_markup=markup, parse_mode='HTML')

    return True


def show_status_selected_menu(call, selected_ip):
    """Show CoAP endpoints immediately after selecting an IP in /status."""
    status_text = (
        f"<b>CoAP Endpoints for selected IP</b>\n\n"
        f"IPv6: <code>{selected_ip}</code>\n\n"
        f"Select a CoAP endpoint:"
    )
    bot.edit_message_text(
        status_text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=build_status_coap_keyboard(),
        parse_mode='HTML',
    )


def show_status_coap_menu(call):
    """Show CoAP endpoints from the /status flow."""
    selected_ip = user_selected_ip.get(call.from_user.id)
    if not selected_ip:
        bot.edit_message_text(
            "Please select an IP first.",
            call.message.chat.id,
            call.message.message_id,
        )
        return

    text = f"<b>CoAP Endpoints for {selected_ip}</b>\n\nSelect endpoint:"
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=build_status_coap_keyboard("status_back_to_ips"),
        parse_mode='HTML',
    )

# Build command menu dynamically from endpoints
def build_command_menu():
    """Build command menu with essential commands only"""
    commands = [
        BotCommand("start", "Get started"),
        BotCommand("ip", "Select connected node IP"),
        # BotCommand("status", "Show IP and CoAP status menu"),
        # BotCommand("monitor", "Open Raspberry Pi monitor"),
        BotCommand("coap", "Query CoAP endpoints"),
        BotCommand("connected_nodes", "Show connected nodes"),
        BotCommand("disconnected_nodes", "Show disconnected nodes"),
        BotCommand("reboot", "Reboot Raspberry Pi"),
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
        markup = build_ip_selection_keyboard("ip_")

        if not markup:
            bot.reply_to(msg, "No connected nodes available.")
            return

        connected, _, _ = wisun.get_connected_nodes()
        bot.send_message(msg.chat.id, f"<b>Select IP ({len(connected)} connected)</b>", reply_markup=markup, parse_mode='HTML')
    except Exception as e:
        bot.reply_to(msg, f"Error retrieving connected nodes: {e}")


@bot.message_handler(commands=['status'])
def handle_status(msg):
    """Show IP selector that leads to status and CoAP actions."""
    try:
        show_status_ip_menu(msg.chat.id)
    except Exception as e:
        bot.reply_to(msg, f"Error retrieving status menu: {e}")


@bot.message_handler(commands=['monitor'])
def handle_monitor(msg):
    """Send a new Raspberry Pi monitoring dashboard message."""
    try:
        show_monitor_dashboard(msg.chat.id, msg.from_user.id)
    except Exception as e:
        bot.reply_to(msg, f"Monitor error: {e}")


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


@bot.message_handler(commands=['disconnected_nodes'])
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


@bot.message_handler(commands=['reboot'])
def handle_reboot(msg):
    """Reboot the Raspberry Pi system"""
    success, message = reboot_system()
    bot.send_message(msg.chat.id, message)


@bot.callback_query_handler(func=lambda call: call.data.startswith(("display", "camera", "screen", "status", "coap", "ip", "cmd", "monitor")))
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

    if call.data.startswith("status_"):
        if call.data.startswith("status_ip_"):
            selected_ip = call.data[len("status_ip_"):]
            user_selected_ip[user_id] = selected_ip
            show_status_selected_menu(call, selected_ip)
            bot.answer_callback_query(call.id, "IP selected!")
            return

        if call.data == "status_back_to_ips":
            show_status_ip_menu(call.message.chat.id, call.message.message_id)
            bot.answer_callback_query(call.id, "Back to IP selection")
            return

    if call.data.startswith("monitor_"):
        if call.data == "monitor_refresh":
            key = (call.from_user.id, call.message.chat.id)
            monitor_message_state[key] = call.message.message_id
            try:
                show_monitor_dashboard(
                    call.message.chat.id,
                    call.from_user.id,
                    call.message.message_id,
                )
                bot.answer_callback_query(call.id, "Stats refreshed")
            except telebot.apihelper.ApiTelegramException as e:
                err_text = str(e)
                if "message is not modified" in err_text:
                    bot.answer_callback_query(call.id, "Already up to date")
                else:
                    bot.answer_callback_query(call.id, "Refresh failed")
            except Exception:
                bot.answer_callback_query(call.id, "Refresh failed")
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