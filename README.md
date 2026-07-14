# Freelancer new-message Telegram notifier

Simple Python script that watches a screen region for red pixels (the red badge
used by Freelancer when a new message arrives) and sends a Telegram message
when a new red badge is detected.

Quickstart

1. Edit `config.json` and fill `telegram_token` and `telegram_chat_id`.
   The default monitor box is already set to the provided Freelancer badge
   location.

2. Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

3. Run the CLI version:

```powershell
python main.py
```

Getting a Telegram bot token

1. Open Telegram and start a chat with `@BotFather`.
2. Send `/newbot` and follow the prompts to create a new bot.
3. Copy the token from BotFather, then paste it into `config.json`.

Finding your chat ID

- Use `@userinfobot` or `@get_id_bot` in Telegram to retrieve your user ID.
- Or send a message to your bot and use:

```powershell
curl "https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates"
```

Read the `chat.id` field from the JSON response and paste it into `config.json`.

Important: `telegram_chat_id` must be your chat ID or channel username.
Do not use the bot username (for example, `freelancer_newmsg_noti_bot`).
A bot username will cause Telegram to return `400 Bad Request`.

Notes
- This script detects a red-style badge in the cropped region by default.
- You do not need to set an exact RGB value anymore.
- If the monitored region contains red pixels matching a notification badge, it reports a new message.
- If not, it reports no new message.
- For best reliability, keep the monitor box small and focused on the badge area.