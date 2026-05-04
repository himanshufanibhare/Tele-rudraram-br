# WiSUN Network Telegram Bot

Minimal Telegram bot for monitoring WiSUN network node connectivity.

## Files

- `bot_test.py` — main bot script using `pyTelegramBotAPI`
- `requirements.txt` — Python dependencies
- `config/nodes.py` — known WiSUN node IP addresses
- `utils/helpers.py` — shell command utilities
- `utils/wisun_network.py` — network status query class

## Quick Start

1. Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

2. Set your bot token:

```bash
export TELEGRAM_BOT_TOKEN="<your-bot-token>"
```

3. Run the bot:

```bash
python3 bot_test.py
```

## Commands

- `/start` — get started, shows your user id
- `/help` — show all available commands
- `/connected_nodes` — display only connected WiSUN nodes with count
- `/not_connected_nodes` or `/disconnected_nodes` — display only disconnected WiSUN nodes with count
- `/detail` — show details of pole (placeholder)
- `/pole` — control the pole (placeholder)
- `/br` — border router control & status (placeholder)

## Features

- Parses `wsbrd_cli status` output to extract active IPv6 nodes
- Compares active nodes against known node list (11 nodes defined)
- Displays connected and disconnected nodes with ✅ and ❌ indicators
- Shows summary count of total/connected/disconnected nodes
- Official command menu button in Telegram (click "/" or menu icon to see commands)

## Requirements

- `pyTelegramBotAPI` — Telegram bot API
- `wsbrd_cli` available in system PATH (for network status queries)