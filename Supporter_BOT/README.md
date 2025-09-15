# Supporter BOT

A multi-functional Discord bot designed to automate server management and enhance user engagement. The bot features a comprehensive leveling system with role rewards, automated time-channel updates, and media-only channel enforcement, all managed through intuitive slash commands.

## ✨ Key Features

* **🏆 Advanced Leveling System:**
  * Users gain XP for sending messages with a configurable 10-second cooldown.
  * Automatic role rewards upon reaching specific levels.
  * Leaderboards to foster friendly competition.
  * Dedicated channel for level-up notifications.
  * Manual and scheduled automatic XP reset with role removal for seasonal events.
  * Debug commands for troubleshooting level system configuration.

* **🚫 No-Text Channel Enforcement:**
  * Designate channels where only media (images, videos, links) are allowed.
  * Automatically deletes plain-text messages and notifies the user with auto-deletion after 30 seconds.
  * Configurable redirect channel for text-based conversations.
  * Admin and role-based bypass system with full management commands.
  * Enhanced URL detection for better link recognition.

* **⏰ Live Time Channels:**
  * Automatically updates voice channel names to display the current date, India Standard Time (IST), and Japan Standard Time (JST).
  * Keeps your server's international community synchronized with 10-minute updates for time and daily updates for date.

* **⚙️ Easy Configuration:**
  * Simple slash commands for all setup procedures.
  * A `/show-config` command to view all current settings at a glance.
  * Debug commands for troubleshooting and monitoring.
  * Backend powered by Supabase for robust and scalable data storage.

## 🏆 XP & Leveling System Details

The bot uses a simple, linear progression system. Users earn **10 XP** for each message sent (with a 10-second cooldown), and a new level is achieved every **1,000 total XP**.

Here is the breakdown of total XP and messages needed to reach major levels, starting from Level 0.

| Target Level | Total XP Needed | Total Messages Needed |
| :----------- | :-------------- | :-------------------- |
| **Level 1**  | 1,000 XP        | 100 messages          |
| **Level 10** | 10,000 XP       | 1,000 messages        |
| **Level 20** | 20,000 XP       | 2,000 messages        |
| **Level 30** | 30,000 XP       | 3,000 messages        |
| **Level 40** | 40,000 XP       | 4,000 messages        |
| **Level 50** | 50,000 XP       | 5,000 messages        |
| **Level 60** | 60,000 XP       | 6,000 messages        |
| **Level 70** | 70,000 XP       | 7,000 messages        |
| **Level 80** | 80,000 XP       | 8,000 messages        |
| **Level 90** | 90,000 XP       | 9,000 messages        |
| **Level 100**| 100,000 XP      | 10,000 messages       |

## 🤖 Command List

All commands are slash commands and are available by typing `/` in Discord.

### General Commands

| Command                  | Description                                            | Permissions   |
| ------------------------ | ------------------------------------------------------ | ------------- |
| `/help`                  | Show the list of all available bot commands.           | Everyone      |
| `/show-config`           | Display the current configuration for time & no-text.  | Everyone      |

### Leveling Commands

| Command                  | Description                                            | Permissions   |
| ------------------------ | ------------------------------------------------------ | ------------- |
| `/level`                 | Check your or another user's current level and XP.     | Everyone      |
| `/leaderboard`           | Show the top 10 users on the server leaderboard.       | Everyone      |
| `/setup-level-reward`    | Set a role reward for reaching a specific level.       | Administrator |
| `/level-reward-show`     | View all configured level rewards for the server.      | Administrator |
| `/notify-level-msg`      | Set the channel for level-up notification messages.    | Administrator |
| `/set-auto-reset`        | Set an automatic XP reset schedule (in days).          | Administrator |
| `/reset-xp`              | Manually reset all XP/levels and remove reward roles.  | Administrator |
| `/debug-level`           | Debug level system configuration and permissions.      | Administrator |

### No-Text Channel Commands

| Command                  | Description                                            | Permissions   |
| ------------------------ | ------------------------------------------------------ | ------------- |
| `/setup-no-text`         | Restrict a channel to only allow media and links.      | Administrator |
| `/remove-no-text`        | Remove the no-text restriction from a channel.         | Administrator |
| `/bypass-no-text`        | Allow a role to send text in no-text channels.         | Administrator |
| `/show-bypass-roles`     | Show all roles that can bypass no-text restrictions.   | Administrator |
| `/remove-bypass-role`    | Remove a role's ability to bypass no-text channels.    | Administrator |

### Time Channel Commands

| Command                  | Description                                            | Permissions   |
| ------------------------ | ------------------------------------------------------ | ------------- |
| `/setup-time-channels`   | Set up channels for date, India time, and Japan time.  | Administrator |

## 🚀 Setup and Installation Guide

### Step 1: Prerequisites

Before you begin, you will need:

* Python 3.8 or a newer version installed on your system.
* A Discord Bot application with a Token, created on the Discord Developer Portal.
* A free account and a new project set up on Supabase for the database.

### Step 2: Bot Installation

1. Download the project files to your computer.
2. Create and activate a Python virtual environment inside the `Supporter_BOT` folder (recommended).
3. Install all necessary Python libraries by running:

   ```bash
   pip install -r Data_Files/requirements.txt
   ```

### Step 3: Database Configuration

The bot uses a Supabase database to store all user data. In your Supabase project's SQL Editor, create the following six tables:

#### Required Database Tables

1. **`users` Table:**

   ```sql
   CREATE TABLE users (
       guild_id TEXT NOT NULL,
       user_id TEXT NOT NULL,
       username TEXT,
       xp INTEGER DEFAULT 0,
       level INTEGER DEFAULT 0,
       PRIMARY KEY (guild_id, user_id)
   );
   ```

2. **`level_roles` Table:**

   ```sql
   CREATE TABLE level_roles (
       guild_id TEXT NOT NULL,
       level INTEGER NOT NULL,
       role_id TEXT NOT NULL,
       PRIMARY KEY (guild_id, level)
   );
   ```

3. **`level_notify_channel` Table:**

   ```sql
   CREATE TABLE level_notify_channel (
       guild_id TEXT PRIMARY KEY,
       channel_id TEXT NOT NULL
   );
   ```

4. **`last_notified_level` Table:**

   ```sql
   CREATE TABLE last_notified_level (
       guild_id TEXT NOT NULL,
       user_id TEXT NOT NULL,
       level INTEGER DEFAULT 0,
       PRIMARY KEY (guild_id, user_id)
   );
   ```

5. **`bypass_roles` Table:**

   ```sql
   CREATE TABLE bypass_roles (
       guild_id TEXT NOT NULL,
       role_id TEXT NOT NULL,
       PRIMARY KEY (guild_id, role_id)
   );
   ```

6. **`auto_reset` Table:**

   ```sql
   CREATE TABLE auto_reset (
       guild_id TEXT PRIMARY KEY,
       days INTEGER NOT NULL,
       last_reset TIMESTAMP WITH TIME ZONE DEFAULT NOW()
   );
   ```

### Step 4: Environment Variables

Create a file named `.env` inside the `Data_Files` folder with the following variables:

```env
DISCORD_TOKEN=your_bot_token_here
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_public_key
```

**Required credentials:**

1. `DISCORD_TOKEN`: Your bot's token from the Discord Developer Portal
2. `SUPABASE_URL`: The project URL from your Supabase API settings
3. `SUPABASE_KEY`: The `anon` `public` key from your Supabase API settings

### Step 5: Running the Bot

Once everything is configured, run the main script:

```bash
python run_supporter.py
```

## 📂 Project Structure

``` File_Structure
Supporter_BOT/
├── run_supporter.py          # Main startup script
├── Python_Files/             # Core bot modules
│   ├── supporter.py          # Main bot file and command registration
│   ├── level.py              # Complete leveling system with role management
│   ├── no_text.py            # Media-only channel enforcement
│   ├── date_and_time.py      # Automatic time channel updates
│   └── help.py               # Help command management
└── Data_Files/               # Configuration and data storage
    ├── .env                  # Private credentials (create this)
    ├── requirements.txt      # Python dependencies
    ├── no_text.json         # Local no-text channel configs
    └── date_and_time.json   # Local time channel configs
```

### Core Module Details

* **`supporter.py`**: Main bot initialization, event handling, and primary command definitions
* **`level.py`**: Complete XP/leveling system with automatic role rewards, notifications, and role removal on reset
* **`no_text.py`**: Media-only channel management with bypass system and enhanced URL detection  
* **`date_and_time.py`**: Automated time zone display with scheduled updates
* **`help.py`**: Centralized help command system

## 🔧 Bot Permissions Required

The bot needs the following Discord permissions to function properly:

### Essential Permissions

* **Send Messages**: For notifications and command responses

* **Manage Roles**: For automatic role rewards (leveling system)
* **Manage Channels**: For updating time channel names
* **View Channels**: To access configured channels
* **Delete Messages**: For no-text channel enforcement
* **Use Slash Commands**: For all bot interactions

### Recommended Permissions

* **Embed Links**: For rich embeds in leaderboards and help

* **Attach Files**: For potential future features
* **Read Message History**: For comprehensive message handling

## 🐛 Troubleshooting

### Common Issues

1. **Level notifications not working:**
   * Use `/debug-level` to check configuration
   * Ensure notification channel is set with `/notify-level-msg`
   * Verify bot has "Send Messages" permission in notification channel

2. **Role rewards not being assigned:**
   * Check bot has "Manage Roles" permission
   * Ensure bot's highest role is above reward roles
   * Use `/debug-level` to verify role configuration

3. **No-text channels not working:**
   * Verify bot has "Delete Messages" permission
   * Check if user has bypass role or admin permissions
   * Ensure channels are properly configured with `/setup-no-text`

4. **Time channels not updating:**
   * Verify bot has "Manage Channels" permission
   * Check that channels are voice channels (not text channels)
   * Ensure channels are properly configured with `/setup-time-channels`

## 📊 Database Management

The bot automatically manages all database operations, but here are some useful queries for manual management:

### View all users in a guild

```sql
SELECT * FROM users WHERE guild_id = 'YOUR_GUILD_ID' ORDER BY xp DESC;
```

### Reset all XP for a guild

```sql
UPDATE users SET xp = 0, level = 0 WHERE guild_id = 'YOUR_GUILD_ID';
UPDATE last_notified_level SET level = 0 WHERE guild_id = 'YOUR_GUILD_ID';
```

### View level rewards

```sql
SELECT * FROM level_roles WHERE guild_id = 'YOUR_GUILD_ID' ORDER BY level;
```

## 🔄 Auto-Reset Features

The bot includes intelligent auto-reset functionality that:

* Automatically resets all user XP and levels based on configured schedule
* Removes all level reward roles from users before reset
* Tracks reset history to prevent duplicate resets
* Supports both manual and automatic reset options
* Provides detailed feedback on reset operations

This makes it perfect for seasonal events, competitions, or regular server refreshes while maintaining role hierarchy integrity.
