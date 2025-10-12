# Supporter BOT

A multi-functional Discord bot designed to automate server management and enhance user engagement. This bot features a comprehensive leveling system, YouTube notifications, automated time-channel updates, and media-only channel enforcement, all managed through intuitive slash commands. It is built to be robust, scalable, and easy for server administrators to configure.

## ✨ Key Features

* **🏆 Advanced Leveling System:** Engage your community by rewarding users with XP for their activity. The system includes automatic role rewards for reaching new levels, a server-wide leaderboard to foster competition, and a dedicated channel for level-up announcements. For seasonal events, administrators can perform a manual or scheduled automatic reset of all user XP and roles.

* **📢 YouTube Notifications:** Automatically announce new video uploads, livestreams, and premieres from your favorite YouTube channels. Features a customizable message with role mentions and a helper command to easily find any channel's ID.

* **🚫 No-Text Channel Enforcement:** Create dedicated media-only channels where plain text is not allowed. The bot will automatically remove text-only messages and send a temporary notification, guiding users to the correct channel for conversations. A role-based bypass system allows designated members to override this restriction.

* **⏰ Live Time Channels:** Keep your server's international community synchronized with voice channels that automatically update their names to display the current date, India Standard Time (IST), and Japan Standard Time (JST).

* **⚙️ Easy Configuration & Control:** All features are managed through simple slash commands. A dedicated `/show-config` command allows administrators to get a quick overview of all bot settings, while owner-only commands provide full control over the bot's presence in different servers.

***

## 🏆 XP & Leveling System Details

The bot uses a simple, linear progression system where a new level is achieved every **1,000 total XP**. Users earn XP in several ways:

* **Text Messages**: 1 XP per message
* **Image Messages**: 2 XP per message
* **Voice Chat**: 3 XP per 120 seconds of activity

| Target Level  | Total XP Needed   |
| :------------ | :---------------- |
| **Level 1**   | 1,000 XP          |
| **Level 10**  | 10,000 XP         |
| **Level 20**  | 20,000 XP         |
| **Level 30**  | 30,000 XP         |
| **Level 50**  | 50,000 XP         |
| **Level 100** | 100,000 XP        |

## 🤖 Command List

All bot interactions are handled through slash commands available by typing `/` in Discord.

### General Commands

| Command           | Description                                       | Permissions   |
| :---------------- | :------------------------------------------------ | :------------ |
| `/help`           | Shows a list of all available bot commands.       | Everyone      |
| `/show-config`    | Displays the current configuration for the server.| Everyone      |
| `/serverlist`     | Lists all servers the bot is in.                  | Bot Owner     |
| `/leaveserver`    | Forces the bot to leave a server by ID.           | Bot Owner     |
| `/banguild`       | Bans a server and makes the bot leave.            | Bot Owner     |
| `/unbanguild`     | Unbans a server, allowing it to re-invite the bot.| Bot Owner     |

### Leveling Commands

| Command               | Description                                                       | Permissions   |
| :-------------------- | :---------------------------------------------------------------- | :------------ |
| `/level`              | Checks the current level and XP of yourself or another user.      | Everyone      |
| `/leaderboard`        | Shows the top 10 users on the server leaderboard.                 | Everyone      |
| `/setup-level-reward` | Sets a role reward for reaching a specific level.                 | Administrator |
| `/level-reward-show`  | Views all configured level rewards for the server.                | Administrator |
| `/notify-level-msg`   | Sets the channel for level-up notification messages.              | Administrator |
| `/set-auto-reset`     | Sets an automatic XP reset schedule (in days).                    | Administrator |
| `/show-auto-reset`    | Shows the current auto-reset configuration for this server.       | Administrator |
| `/stop-auto-reset`    | Disables the automatic XP reset for this server.                  | Administrator |
| `/reset-xp`           | Manually resets all XP/levels and removes reward roles.           | Administrator |
| `/upgrade-all-roles`  | Manually syncs roles for all users based on their current level.  | Administrator |

### YouTube Notification Commands

| Command                           | Description                                               | Permissions   |
| :-------------------------------- | :-------------------------------------------------------- | :------------ |
| `/find-youtube-channel-id`        | Finds a channel's ID using its @handle or custom name.    | Everyone      |
| `/setup-youtube-notifications`    | Sets up notifications for a specific YouTube channel.     | Administrator |
| `/disable-youtube-notifications`  | Disables notifications for a configured YouTube channel.  | Administrator |

### No-Text Channel Commands

| Command               | Description                                           | Permissions   |
| :-------------------- | :---------------------------------------------------- | :------------ |
| `/setup-no-text`      | Restricts a channel to only allow media and links.    | Administrator |
| `/remove-no-text`     | Removes the no-text restriction from a channel.       | Administrator |
| `/bypass-no-text`     | Allows a role to send text in no-text channels.       | Administrator |
| `/show-bypass-roles`  | Shows all roles that can bypass no-text restrictions. | Administrator |
| `/remove-bypass-role` | Removes a role's ability to bypass no-text channels.  | Administrator |

### Time Channel Commands

| Command                   | Description                                               | Permissions   |
| :------------------------ | :-------------------------------------------------------- | :------------ |
| `/setup-time-channels`    | Sets up channels for date, India time, and Japan time.    | Administrator |

## 📂 Project Structure

``` Files Structure
Tester/
├── run_supporter.py          # Main startup script to run the bot.
├── Python_Files/             # Contains all core bot modules.
│   ├── supporter.py          # Main bot file, event handling, and command registration.
│   ├── level.py              # Manages the complete leveling system and database interactions.
│   ├── no_text.py            # Handles media-only channel enforcement and bypass logic.
│   ├── date_and_time.py      # Controls the automatic updates for time channels.
│   ├── youtube_notification.py # Manages YouTube upload and stream notifications.
│   ├── owner_actions.py      # Handles owner-exclusive commands like leaving/banning servers.
│   └── help.py               # Manages the help command and its display.
└── Data_Files/               # For configuration, data storage, and dependencies.
    ├── .env                  # Stores private credentials like bot token and database keys.
    ├── requirements.txt      # Lists all Python libraries required for the project.
    ├── no_text.json          # Stores local configuration for no-text channels.
    └── date_and_time.json    # Stores local configuration for time channels.
```

## 🚀 Setup and Installation Guide

### Step 1: Prerequisites

Before you begin, you will need:

* Python 3.8 or a newer version installed.
* A Discord Bot application created on the Discord Developer Portal.
* A free project set up on a PostgreSQL database.
* A Google Cloud Project with the **YouTube Data API v3** enabled to get an API key.

### Step 2: Bot Installation

Download the project files to your computer. It is highly recommended to create and activate a Python virtual environment inside the project folder. Once your environment is active, install all the necessary Python libraries by running the command to install from the `requirements.txt` file.

### Step 3: Database Configuration

The bot uses a database to store all persistent data. In your Database project's SQL Editor, you will need to create the required tables for the bot to function, including tables for `users`, `level_roles`, `level_notify_channel`, `last_notified_level`, `bypass_roles`, `auto_reset`, `youtube_notifications`, and `banned_guilds`.

### Step 4: Environment Variables

Create a new file named `.env` inside the `Data_Files` folder. In this file, you must provide your bot's private token from the Discord Developer Portal, the URL and public key from your Database project's API settings, and your **YouTube Data API v3 key** from the Google Cloud Console.

### Step 5: Running the Bot

Once all the previous steps are completed and your credentials are in place, you can run the main startup script to bring the bot online in your server.
