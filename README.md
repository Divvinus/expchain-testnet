# Somnia Bot

<div align="center">

```
________   _______     _           _         ____        _   
|  ____\ \ / /  __ \   | |         (_)       |  _ \      | |  
| |__   \ V /| |__) |__| |__   __ _ _ _ __   | |_) | ___ | |_ 
|  __|   > < |  ___/ __| '_ \ / _` | | '_ \  |  _ < / _ \| __|
| |____ / . \| |  | (__| | | | (_| | | | | | | |_) | (_) | |_ 
|______/_/ \_\_|   \___|_| |_|\__,_|_|_| |_| |____/ \___/ \__|
```

<a href="https://t.me/divinus_xyz">
    <img src="https://img.shields.io/badge/Telegram-Channel-blue?style=for-the-badge&logo=telegram" alt="Telegram Channel">
</a>
<a href="https://t.me/divinus_py">
    <img src="https://img.shields.io/badge/Telegram-Contact-blue?style=for-the-badge&logo=telegram" alt="Telegram Contact">
</a>
<br>
<b>Multifunctional bot for automating interaction with EXPchain test network</b>
</div>

## 📋 Table of Contents

- [Features](#-features)
- [Key Benefits](#-key-benefits)
- [System Requirements](#-system-requirements)
- [Installation](#️-installation)
- [Configuration Guide](#️-configuration-guide)
  - [Setup Configuration Files](#1-setup-configuration-files)
  - [Advanced Configuration](#2-advanced-configuration)
  - [Discord Setup Instructions](#3-discord-setup-instructions)
  - [Settings Configuration](#4-settings-configuration)
- [Running the Bot](#-running-the-bot)
- [Available Commands](#-available-commands)
- [Security Best Practices](#-security-best-practices)
- [Contributing](#-contributing)
- [License](#-license)
- [Disclaimer](#️-disclaimer)
- [Support](#-support)

## 🚀 Features

Somnia Bot is designed to automate various operations in the EXPchain test network:

- **Web3 Automation**
  - 🚰 **Faucet** - Request and receive test tokens automatically
  - 🌉 **Bridge** - Transfer assets between BSC and Sepolia test networks
  - 💱 **Swap** - Execute token swaps with optimized settings

## 🍀 Key Benefits

- **Smart Data Management** - Automatic validation of data with invalid entries saved to separate files
- **Integrated Notifications** - Automatic statistics reporting via Telegram
- **User-Friendly Configuration** - All user data conveniently managed in a single Excel file
- **Flexible Proxy Support** - Full compatibility with HTTP, HTTPS, and SOCKS5 proxies

## 📋 System Requirements

- Python 3.11 or higher
- Windows or Linux operating system
- Active Discord account

## 🛠️ Installation

1. Clone the repository:
```bash
git clone [repository URL]
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # for Linux
.\venv\Scripts\activate   # for Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## ⚙️ Configuration Guide

### 1. Setup Configuration Files

Create the following structure in the `config/data/client/` directory:

#### accounts.xlsx
Your Excel file must contain these columns:
- `Private Key` (required) - Wallet private key for transactions
- `Proxy` (optional) - Proxy in the format described below
- `Discord Token` (optional) - Your Discord authentication token

#### Proxy Configuration
The bot supports the following proxy formats:

```
# HTTP/HTTPS Proxies
http://123.45.67.89:8080
https://[2001:db8::1]:8080 (IPv6)
http://user:pass@123.45.67.89:8080
https://user:pass@[2001:db8::1]:8080 (IPv6)

# SOCKS5 Proxies
socks5://123.45.67.89:1080
socks5://[2001:db8::1]:1080 (IPv6)
socks5://user:pass@123.45.67.89:1080
socks5://user:pass@[2001:db8::1]:1080 (IPv6)
```

### 2. Advanced Configuration

For experienced users, additional configuration options are available in the `configs.py` file.

### 3. Discord Setup Instructions

1. Obtain your Discord token (found in network request headers as "authorization")
2. Ensure the token begins with "MTI" or contains a valid alphanumeric token
3. Add the token to your accounts.xlsx file

### 4. Settings Configuration

Edit the `config/settings.yaml` file with your preferred settings:

```yaml
#------------------------------------------------------------------------------
# Threading Configuration
#------------------------------------------------------------------------------
# Controls parallel execution capacity (min: 1)
threads: 10

#------------------------------------------------------------------------------
# Timing Settings
#------------------------------------------------------------------------------
# Initial delay range before starting operations (seconds)
delay_before_start:
    min: 10
    max: 30

# Delay between tasks (seconds)
delay_between_tasks:
    min: 100
    max: 300

# Telegram Notification Settings
send_stats_to_telegram: true
tg_token: ""  # Get from https://t.me/BotFather
tg_id: ""     # Get from https://t.me/getmyid_bot
```

## 🚀 Running the Bot

Start the bot with:
```bash
python run.py
```

## 📚 Available Commands

After launching the bot, you'll have access to these operations:

1. 🚰 **Faucet** - Request test tokens
2. 🎢 **Bridge BSC** - Transfer tokens from BSC testnet
3. 🏞️ **Bridge Sepolia** - Transfer tokens from Sepolia testnet
4. 🔄 **Swap** - Exchange tokens
5. 💰 **Deploy Contract** - Create your own token
6. 🚪 **Exit** - Close the application

## 🔒 Security Best Practices

1. **Private Key Protection**
   - Never share your private keys or mnemonic phrases
   - Store sensitive data in encrypted storage
   - Consider using environment variables for sensitive credentials

2. **Proxy Security**
   - Use reliable and secure proxy providers
   - Regularly rotate proxies to prevent IP blocking
   - Verify proxy connectivity before operations

3. **Account Security**
   - Regularly update your Discord and other platform tokens
   - Use dedicated accounts for automated operations
   - Implement proper encryption for stored credentials

4. **Rate Limiting Awareness**
   - Respect platform-specific rate limits
   - Configure appropriate delays between operations
   - Avoid patterns that might trigger security systems

## 🤝 Contributing

### How to Contribute

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/YourFeature`)
3. Commit your changes (`git commit -m 'Add YourFeature'`)
4. Push to the branch (`git push origin feature/YourFeature`)
5. Open a Pull Request

### Development Standards

- Follow PEP 8 Python style guide
- Write clear, documented code with appropriate comments
- Include type hints for better code quality
- Add unit tests for new functionality
- Update documentation to reflect changes

## 📜 License

This project is distributed under the MIT License. See `LICENSE` file for more information.

## ⚠️ Disclaimer

Use this bot at your own risk. The developers are not responsible for any consequences of using this bot, including but not limited to account restrictions or loss of funds.

## 📞 Support

For questions, issues, or support, please contact us through our Telegram channels listed at the top of this document.