# Supporter BOT

A multi-functional Discord bot designed to automate server management and enhance user engagement. The bot features a comprehensive leveling system, automated time-channel updates, and media-only channel enforcement, all managed through intuitive slash commands.

## ✨ Key Features

* **🏆 Advanced Leveling System:**
  * Users gain XP for sending messages with a configurable cooldown.
  * Automatic role rewards upon reaching specific levels.
  * Leaderboards to foster friendly competition.
  * Dedicated channel for level-up notifications.
  * Manual and scheduled automatic XP reset for seasonal events.

* **🚫 No-Text Channel Enforcement:**
  * Designate channels where only media (images, videos, links) are allowed.
  * Automatically deletes plain-text messages and notifies the user.
  * Configurable redirect channel for text-based conversations.
  * Admin and role-based bypass system.

* **⏰ Live Time Channels:**
  * Automatically updates voice channel names to display the current date, India Standard Time (IST), and Japan Standard Time (JST).
  * Keeps your server's international community synchronized.

* **⚙️ Easy Configuration:**
  * Simple slash commands for all setup procedures.
  * A `/show-config` command to view all current settings at a glance.
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

| Command                  | Description                                            | Permissions   |
| ------------------------ | ------------------------------------------------------ | ------------- |
| `/help`                  | Show the list of all available bot commands.           | Everyone      |
| `/show-config`           | Display the current configuration for time & no-text.  | Everyone      |
| `/level`                 | Check your or another user's current level and XP.     | Everyone      |
| `/leaderboard`           | Show the top 10 users on the server leaderboard.       | Everyone      |
| `/setup-time-channels`   | Set up channels for date, India time, and Japan time.  | Administrator |
| `/setup-no-text`         | Restrict a channel to only allow media and links.      | Administrator |
| `/remove-no-text`        | Remove the no-text restriction from a channel.         | Administrator |
| `/bypass-no-text`        | Allow a role to send text in no-text channels.         | Administrator |
| `/setup-level-reward`    | Set a role reward for reaching a specific level.       | Administrator |
| `/level-reward-show`     | View all configured level rewards for the server.      | Administrator |
| `/notify-level-msg`      | Set the channel for level-up notification messages.    | Administrator |
| `/set-auto-reset`        | Set an automatic XP reset schedule (in days).          | Administrator |
| `/reset-xp`              | Manually reset all XP and levels for everyone.         | Administrator |

## 🚀 Setup and Installation Guide

### Step 1: Prerequisites

Before you begin, you will need:

* Python 3.8 or a newer version installed on your system.
* A Discord Bot application with a Token, created on the Discord Developer Portal.
* A free account and a new project set up on Supabase for the database.

### Step 2: Bot Installation

First, download the project files to your computer. It is highly recommended to create and activate a Python virtual environment inside the `Supporter_BOT` folder to manage dependencies. Then, install all the necessary Python libraries by running the `requirements.txt` file located in the `Data_Files` directory.

### Step 3: Database Configuration

The bot uses a Supabase database to store all user data. In your Supabase project's SQL Editor, you must create six tables with the following structure:

* **`users` Table:** Stores the XP and level for each user. It needs columns for `guild_id`, `user_id`, `xp`, and `level`.
* **`level_roles` Table:** Stores the roles to be awarded at certain levels. It needs columns for `guild_id`, `level`, and `role_id`.
* **`level_notify_channel` Table:** Stores the channel ID for level-up notifications. It needs columns for `guild_id` and `channel_id`.
* **`last_notified_level` Table:** Tracks the last level a user was notified for to prevent spam. It needs columns for `guild_id`, `user_id`, and `level`.
* **`bypass_roles` Table:** Stores roles that can bypass the no-text channel rules. It needs columns for `guild_id` and `role_id`.
* **`auto_reset` Table:** Stores the automatic XP reset schedule. It needs columns for `guild_id`, `days`, and `last_reset`.

### Step 4: Environment Variables

Create a file named `.env` inside the `Data_Files` folder. This file will securely store your bot's secret credentials. You need to add three variables to this file:

1. `DISCORD_TOKEN`: Your bot's token from the Discord Developer Portal.
2. `SUPABASE_URL`: The project URL from your Supabase API settings.
3. `SUPABASE_KEY`: The `anon` `public` key from your Supabase API settings.

### Step 5: Running the Bot

Once everything is configured, run the `run_supporter.py` script to start the bot.

## 📂 Project Structure

The project is organized into several key files and directories:

* **`run_supporter.py`**: The main script used to start the bot.
* **`Python_Files/`**: This directory contains the core logic for each feature.
  * `supporter.py`: The main bot file where all modules are initialized and commands are registered.
  * `level.py`: Manages the entire leveling system.
  * `no_text.py`: Manages the media-only channel feature.
  * `date_and_time.py`: Manages the automatic time channel updates.
  * `help.py`: Manages the `/help` command.
* **`Data_Files/`**: This directory stores configuration and data.
  * `.env`: Your private credentials.
  * `requirements.txt`: A list of all Python libraries the bot needs.
  * `no_text.json` & `date_and_time.json`: Local storage for channel configurations.
