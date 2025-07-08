# AI Trading Bot

An AI-powered automated forex trading bot that uses OpenAI for market analysis and executes trades through FXOpen with Telegram monitoring.

## Features

- **AI-Powered Analysis**: Uses OpenAI GPT-4o for intelligent market analysis
- **FXOpen Integration**: Live trading through FXOpen broker API
- **Telegram Monitoring**: Real-time notifications and bot control
- **Risk Management**: Multi-layered failsafe mechanisms
- **Performance Tracking**: Comprehensive trade analytics and reporting
- **Automated Trading**: Hands-free trading with configurable parameters

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

Or install individually:
```bash
pip install openai aiohttp python-telegram-bot matplotlib numpy python-dotenv
```

### 2. Environment Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Required environment variables:
- `OPENAI_API_KEY` - Your OpenAI API key
- `TELEGRAM_BOT_TOKEN` - Telegram bot token (optional)
- `TELEGRAM_CHAT_ID` - Telegram chat ID (optional)
- `FXOPEN_LOGIN` - FXOpen account login
- `FXOPEN_PASSWORD` - FXOpen account password
- `FXOPEN_SERVER` - FXOpen server
- `FXOPEN_API_KEY` - FXOpen API key
- `FXOPEN_API_SECRET` - FXOpen API secret

### 3. Running with PM2

Install PM2 globally:
```bash
npm install -g pm2
```

Start the bot:
```bash
pm2 start main.py --name "ai-trading-bot" --interpreter python3
```

Monitor the bot:
```bash
pm2 logs ai-trading-bot
pm2 status
```

Stop the bot:
```bash
pm2 stop ai-trading-bot
```

Restart the bot:
```bash
pm2 restart ai-trading-bot
```

### 4. Configuration Options

Key trading parameters (set in `.env`):
- `MAX_RISK_PERCENT=2.0` - Maximum risk per trade
- `MAX_DAILY_LOSS_PERCENT=5.0` - Daily loss limit
- `STOP_LOSS_PIPS=20` - Default stop loss
- `TAKE_PROFIT_PIPS=40` - Default take profit
- `SCAN_INTERVAL=30` - Market scan interval in seconds

## Project Structure

- `main.py` - Main application entry point
- `ai_analyzer.py` - OpenAI market analysis
- `fxopen_handler.py` - FXOpen broker integration
- `telegram_bot.py` - Telegram notifications and control
- `trader.py` - Core trading logic
- `earnings_tracker.py` - Performance tracking
- `failsafe.py` - Risk management
- `logger.py` - Logging configuration
- `screenshot.py` - Trade documentation
- `config.py` - Configuration management

## Important Notes

1. **Demo Mode**: The bot runs in simulation mode if FXOpen credentials are not provided
2. **Risk Management**: Always test with small amounts first
3. **Monitoring**: Use Telegram bot for real-time monitoring
4. **Logs**: Check `logs/trading_bot.log` for detailed information
5. **Data**: Trade history stored in `data/` directory

## Support

For issues or questions, check the logs first:
```bash
tail -f logs/trading_bot.log
```

## Disclaimer

This bot is for educational and research purposes. Trading involves significant risk. Use at your own risk and never trade more than you can afford to lose.