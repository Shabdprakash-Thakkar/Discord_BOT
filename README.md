# Supporter BOT — Full Project Documentation

A complete guide for developers—especially beginners—who want to understand, configure, and extend the **Supporter BOT**, a multi‑functional Discord bot built with Python, PostgreSQL, and Discord's Slash Command system.

---

# 📌 1. Introduction

The **Supporter BOT** is a feature-rich Discord automation system designed to help community servers manage:

* User engagement (XP, leveling, leaderboards)
* Channel cleanliness (media-only, no links, no Discord invites)
* YouTube upload notifications
* Auto-updating time channels
* Server owner control (ban/unban servers, leave servers)

This documentation is written for **new developers**, providing clear explanations of each module and system.

---

# 📦 2. Key Features Overview

### ⭐ Leveling System

* Gain XP from text messages, images, and voice chat.
* Level up every 1000 XP.
* Automatically give level‑reward roles.
* Leaderboard system.
* Auto-reset and manual XP reset.

### ⭐ YouTube Notifications (RSS-Based)

* Detects new YouTube uploads every 15 minutes.
* Zero API quota usage.
* Ability to find YouTube channel ID.
* Auto-seeds old videos to prevent spam.

### ⭐ Channel Restriction System

* Media-only channels (no plain text).
* No Discord invite links.
* Block all types of URLs.
* Custom bypass roles.

### ⭐ Time & Date Channels

* Auto-update voice channels with:

  * Current date (midnight reset)
  * IST time
  * JST time

### ⭐ Owner Commands

* List all servers the bot is in.
* Force the bot to leave a server.
* Ban or unban a server.

---

# 🗂️ 3. Project Folder Structure

```
Supporter_BOT/
├── run_supporter.py         # Starts the bot
├── Python_Files/
│   ├── supporter.py         # Main bot logic and manager loader
│   ├── help.py              # Handles the /g1-help command
│   ├── level.py             # Full leveling system
│   ├── youtube_notification.py # YouTube RSS notifications
│   ├── no_text.py           # Channel restriction systems
│   ├── owner_actions.py     # Bot owner-only commands
│   └── date_and_time.py     # Auto-updating time channels
└── Data_Files/
    ├── .env                 # Environment configuration
    ├── requirements.txt     # Python dependencies
    └── SQL-Editor-Code-Supabase.txt # Database schema
```

---

# 🧩 4. Installation Guide

## Step 1 — Install Requirements

Make sure you have:

* Python 3.9+
* PostgreSQL (or Supabase)
* A Discord Bot Token

Create a virtual environment:

```
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

Install dependencies:

```
pip install -r Data_Files/requirements.txt
```

## Step 2 — Setup the `.env` File

Create `Data_Files/.env`:

```
DISCORD_TOKEN=your_bot_token
DATABASE_URL=your_postgres_database_url
```

## Step 3 — Database Setup

Run the SQL file: `SQL-Editor-Code-Supabase.txt`
It creates all required tables:

* users
* level_roles
* last_notified_level
* youtube_notification_config
* youtube_notification_logs
* bypass_roles
* auto_reset
* time_channel_config
* no_text_channels
* no_discord_links_channels
* no_links_channels
* banned_guilds

---

# ⚙️ 5. How the Bot Works (System Overview)

## 5.1 SupporterBot Class (Main Controller)

Located in `supporter.py`:

* Loads all managers
* Connects to PostgreSQL
* Syncs Slash Commands globally
* Runs background tasks

Managers loaded:

* LevelManager
* NoTextManager
* DateTimeManager
* YouTubeManager
* OwnerActionsManager
* HelpManager

---

# 🧠 6. Leveling System (level.py)

The bot awards XP based on:

* **10 XP** → normal message
* **15 XP** → message with image
* **4 XP per minute** → voice activity (max 1500 per reset cycle)

### How levels work

* XP → Level calculation: `level = xp // 1000`
* Level-up event triggers:

  * Role upgrade
  * Level-up notification
  * Log in database

### Auto-Reset

Admins can:

* `/l6-set-auto-reset` (1–365 days)
* `/l7-show-auto-reset`
* `/l8-stop-auto-reset`

### Commands Summary

* `/l1-level`
* `/l2-leaderboard`
* `/l3-setup-level-reward`
* `/l4-level-reward-show`
* `/l5-notify-level-msg`
* `/l9-reset-xp`
* `/l10-upgrade-all-roles`

---

# 🔗 7. Channel Restriction System (no_text.py)

Three rule categories:

### 1. No-Text Channels (media-only)

* Deletes plain text messages
* Only allows images, links, embeds
* Auto-warns user with message

### 2. No Discord Links

Blocks:

* discord.gg/
* discord.com/invite/

### 3. No Links (ALL links)

Deletes **any** URL silently.

### Commands Summary

* `/n1-setup-no-text`
* `/n2-remove-no-text`
* `/n3-bypass-no-text`
* `/n4-show-bypass-roles`
* `/n5-remove-bypass-role`
* `/n6-no-discord-link`
* `/n7-no-links`
* `/n8-remove-no-discord-link`
* `/n9-remove-no-links`

---

# ⏰ 8. Time & Date Channels (date_and_time.py)

### Features:

* Updates IST and JST time every 10 minutes
* Updates date at midnight IST
* Auto-aligned tasks

### Command:

* `/t1-setup-time-channels` → Provide 3 voice channels

---

# 📺 9. YouTube RSS Notification System (youtube_notification.py)

### What it does:

* Monitors YouTube via RSS (no API quota)
* Detects new uploads
* Sends announcement with optional role mention

### Smart Features:

* Auto-seeds old videos into DB to avoid spam
* Only notifies videos newer than 2 days
* Fetches every 15 minutes

### Commands:

* `/y1-find-youtube-channel-id`
* `/y2-setup-youtube-notifications`
* `/y3-disable-youtube-notifications`
* `/y4-bulk-seed-all-videos` (Admin only)
* `/y5-test-rss-feed`

---

# 👑 10. Owner-Only Commands (owner_actions.py)

Commands only bot owner can run:

* `/g3-serverlist`
* `/g4-leaveserver`
* `/g5-banguild`
* `/g6-unbanguild`

Used to manage where the bot is allowed to be.

---

# 🆘 11. Help System (help.py)

The bot includes a fully formatted help command:

```
/g1-help
```

Shows:

* All features
* All commands grouped by category
* Owner commands only if user is bot owner

---

# 🚀 12. Running the Bot

Start the bot with:

```
python run_supporter.py
```

You should see logs:

* Database connected
* Managers initialized
* Slash commands synced

---

# 🧪 13. Testing Checklist

Before deployment, verify:

### Database Working?

* Connected successfully
* Tables exist
* Data inserts correctly

### Commands Registered?

Use `/` in Discord to confirm.

### Permissions?

Bot must have:

* Manage Roles
* Manage Channels
* Manage Messages
* View Channels
* Read & Send Messages

### Background Tasks Running?

* YouTube checks every 15 mins
* Time updates every 10 mins
* Date resets at midnight IST

---

# 🧑‍💻 14. Common Troubleshooting

### Bot Not Responding?

* Token incorrect
* Slash commands not synced
* Missing permissions

### Leveling Not Working?

* Database disconnected
* Level rewards not set
* No notify channel set

### YouTube Not Working?

* Invalid YouTube channel ID
* RSS feed blocked
* Missing message permission in target channel

---

# 📌 15. Future Improvement Ideas

* Web dashboard for configuration
* Custom XP rate settings
* Multi-language support
* Full YouTube API integration
* Auto-backups for database
* Add many More Usefull features

---

# ❤️ 16. Credits

Developed with love for Discord communities.

Thank you for using **Supporter BOT**!
