# Supporter BOT

A multi-functional Discord bot designed to automate server management and enhance user engagement. This bot features a comprehensive leveling system, YouTube notifications, automated time-channel updates, and advanced media/link control systems, all managed through intuitive slash commands. It is built to be robust, scalable, and easy for server administrators to configure.

## ✨ Key Features

* **🏆 Advanced Leveling System:** Engage your community by rewarding users with XP for their activity. The system includes automatic role rewards for reaching new levels, a server-wide leaderboard to foster competition, and a dedicated channel for level-up announcements. For seasonal events, administrators can perform a manual or scheduled automatic reset of all user XP and roles.

* **📢 YouTube Notifications:** Automatically announce new video uploads, livestreams, and premieres from your favorite YouTube channels. Features a customizable message with role mentions and a helper command to easily find any channel's ID.

* **🚫📝 No-Text Channel Enforcement:** Create dedicated media-only channels where plain text is not allowed. The bot will automatically remove text-only messages and send a temporary notification, guiding users to the correct channel for conversations. A role-based bypass system allows designated members to override this restriction.

* **🔗 Advanced Link Control System:** Three-tier link restriction system to maintain channel quality:
  * **No Discord Links**: Blocks Discord server/channel invite links (discord.gg, discord.com/invite) to prevent server promotion while allowing all other links (YouTube, Instagram, etc.)
  * **No Links**: Most restrictive - blocks ALL links silently
  * Role-based bypass system applies to all restrictions

* **⏰ Live Time Channels:** Keep your server's international community synchronized with voice channels that automatically update their names to display the current date, India Standard Time (IST), and Japan Standard Time (JST).

* **⚙️ Easy Configuration & Control:** All features are managed through simple slash commands. A dedicated `/g2-show-config` command allows administrators to get a quick overview of all bot settings, while owner-only commands provide full control over the bot's presence in different servers.

***

## 🏆 XP & Leveling System Details

The bot uses a simple, linear progression system where a new level is achieved every **1,000 total XP**. Users earn XP in several ways:

* **Text Messages**: 10 XP per message
* **Image Messages**: 15 XP per message
* **Voice Chat**: 4 XP per 60 seconds of activity (capped at 1,500 XP per reset period)

## 🤖 Command List

All bot interactions are handled through slash commands available by typing `/` in Discord.

### General Commands

| Command           | Description                                       | Permissions   |
| :---------------- | :------------------------------------------------ | :------------ |
| `/g1-help`        | Shows a list of all available bot commands.       | Everyone      |
| `/g2-show-config` | Displays the current configuration for the server.| Everyone      |
| `/g3-serverlist`  | Lists all servers the bot is in.                  | Bot Owner     |
| `/g4-leaveserver` | Forces the bot to leave a server by ID.           | Bot Owner     |
| `/g5-banguild`    | Bans a server and makes the bot leave.            | Bot Owner     |
| `/g6-unbanguild`  | Unbans a server, allowing it to re-invite the bot.| Bot Owner     |

### Leveling Commands

| Command                  | Description                                                       | Permissions   |
| :----------------------- | :---------------------------------------------------------------- | :------------ |
| `/l1-level`              | Checks the current level and XP of yourself or another user.      | Everyone      |
| `/l2-leaderboard`        | Shows the top 10 users on the server leaderboard.                 | Everyone      |
| `/l3-setup-level-reward` | Sets a role reward for reaching a specific level.                 | Administrator |
| `/l4-level-reward-show`  | Views all configured level rewards for the server.                | Administrator |
| `/l5-notify-level-msg`   | Sets the channel for level-up notification messages.              | Administrator |
| `/l6-set-auto-reset`     | Sets an automatic XP reset schedule (1-365 days).                 | Administrator |
| `/l7-show-auto-reset`    | Shows the current auto-reset configuration for this server.       | Administrator |
| `/l8-stop-auto-reset`    | Disables the automatic XP reset for this server.                  | Administrator |
| `/l9-reset-xp`           | Manually resets all XP/levels and removes reward roles.           | Administrator |
| `/l10-upgrade-all-roles` | Manually syncs roles for all users based on their current level.  | Administrator |

### YouTube Notification Commands

| Command                              | Description                                               | Permissions   |
| :----------------------------------- | :-------------------------------------------------------- | :------------ |
| `/y1-find-youtube-channel-id`        | Finds a channel's ID using its @handle or custom name.    | Everyone      |
| `/y2-setup-youtube-notifications`    | Sets up notifications for a specific YouTube channel.     | Administrator |
| `/y3-disable-youtube-notifications`  | Disables notifications for a configured YouTube channel.  | Administrator |

### No-Text Channel Commands

| Command                  | Description                                           | Permissions   |
| :----------------------- | :---------------------------------------------------- | :------------ |
| `/n1-setup-no-text`      | Restricts a channel to only allow media and links.    | Administrator |
| `/n2-remove-no-text`     | Removes the no-text restriction from a channel.       | Administrator |
| `/n3-bypass-no-text`     | Allows a role to send text in no-text channels.       | Administrator |
| `/n4-show-bypass-roles`  | Shows all roles that can bypass no-text restrictions. | Administrator |
| `/n5-remove-bypass-role` | Removes a role's ability to bypass no-text channels.  | Administrator |

### Link Restriction Commands

| Command                        | Description                                                          | Permissions   |
| :----------------------------- | :------------------------------------------------------------------- | :------------ |
| `/n6-no-discord-link`          | Blocks Discord invite links to prevent server promotion (allows other links). | Administrator |
| `/n7-no-links`                 | Blocks ALL links silently (most restrictive).                        | Administrator |
| `/n8-remove-no-discord-link`   | Removes Discord invite link restriction from a channel.              | Administrator |
| `/n9-remove-no-links`          | Removes all link restrictions from a channel.                        | Administrator |

### Time Channel Commands

| Command                      | Description                                               | Permissions   |
| :--------------------------- | :-------------------------------------------------------- | :------------ |
| `/t1-setup-time-channels`    | Sets up channels for date, India time, and Japan time.    | Administrator |

## 📂 Project Structure

``` Files
Tester/
├── run_supporter.py          # Main startup script to run the bot.
├── Python_Files/             # Contains all core bot modules.
│   ├── supporter.py          # Main bot file, event handling, and command registration.
│   ├── level.py              # Manages the complete leveling system and database interactions.
│   ├── no_text.py            # Handles media-only channel enforcement, link restrictions, and bypass logic.
│   ├── date_and_time.py      # Controls the automatic updates for time channels.
│   ├── youtube_notification.py # Manages YouTube upload and stream notifications.
│   ├── owner_actions.py      # Handles owner-exclusive commands like leaving/banning servers.
│   └── help.py               # Manages the help command and its display.
└── Data_Files/               # For configuration, data storage, and dependencies.
    ├── .env                  # Stores private credentials like bot token and database keys.
    ├── requirements.txt      # Lists all Python libraries required for the project.
    └── Database-Schema       # Design Database. 
```

## 🚀 Setup and Installation Guide

### Step 1: Prerequisites

Before you begin, you will need:

* Python 3.8 or a newer version installed.
* A Discord Bot application created on the [Discord Developer Portal](https://discord.com/developers/applications).
* A Project set up with a PostgreSQL database.
* A Google Cloud Project with the **YouTube API** enabled to get an API key.

### Step 2: Bot Installation

1. Download or clone the project files to your computer.
2. Create and activate a Python virtual environment (recommended):

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install all required Python libraries:

   ```bash
   pip install -r Data_Files/requirements.txt
   ```

### Step 3: Database Configuration

The bot uses (PostgreSQL) to store all persistent data. In your Database project's SQL Editor, run the complete database setup script to create all required tables:

**Required Tables:**

* `users` - Stores user XP, levels, and voice XP
* `level_roles` - Stores role rewards for levels
* `level_notify_channel` - Stores notification channel configuration
* `last_notified_level` - Tracks last notified level per user
* `bypass_roles` - Stores roles that can bypass restrictions
* `auto_reset` - Stores automatic XP reset configuration
* `youtube_notifications` - Stores YouTube channel notification settings
* `banned_guilds` - Stores banned server IDs
* `no_discord_links_channels` - Stores channels with Discord link restrictions
* `no_links_channels` - Stores channels with all link restrictions

Run the SQL script provided in the project documentation to set up all tables with proper indexes and constraints.

### Step 4: Environment Variables

Create a new file named `.env` inside the `Data_Files` folder with the following structure:

```env
# Discord Bot Configuration
DISCORD_TOKEN=your_discord_bot_token_here
DISCORD_CLIENT_ID=your_discord_client_id_here

# Supabase Configuration
DATABASE_URL=your_database_project_url_here
DATABASE_KEY=your_database_anon_public_key_here

# YouTube API Configuration
YOUTUBE_API_KEY=your_youtube_api_key_here
```

### Step 5: Running the Bot

Once all the previous steps are completed and your credentials are in place, run the bot:

```bash
python run_supporter.py
```

The bot will:

1. Connect to your database
2. Initialize all feature managers
3. Sync slash commands globally
4. Display a list of servers it's connected to
5. Start background tasks for time updates, XP management, and YouTube notifications

### Step 6: Inviting the Bot to Your Server

1. Go to Discord Developer Portal → Your Application → OAuth2 → URL Generator
2. Select scopes: `bot` and `applications.commands`
3. Select bot permissions:
   * Manage Roles
   * Manage Channels
   * Send Messages
   * Manage Messages
   * Read Message History
   * Mention Everyone
   * View Channels
4. Copy the generated URL and open it in your browser to invite the bot

## 📝 Notes

* All link restrictions delete messages **silently** with no warning.
* Administrators and server owners automatically bypass all restrictions.
* The voice XP cap resets when the server's XP is reset (manual or automatic).
* Time channels update every 10 minutes, date channels update daily at midnight IST.
* YouTube notifications check for new content every 15 minutes with a 1-hour cooldown per channel.

## 🤝 Support

For issues, questions, or feature requests, please contact the bot developer or refer to the documentation provided with your bot instance.

------------------------------------------

**Made with ❤️ for Discord communities**
