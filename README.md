

# 📇 OsintRat 🐀 Search Bot

A simple Telegram bot that performs ultra-fast searches through a massive synthetic dataset (up to **100M+ records**) powered by **[Meilisearch](https://www.meilisearch.com/)**.  
Originally created as a portfolio experiment in Big Data indexing and search optimization.

🔒 Data Disclaimer

All records used by this project are synthetically generated. Any resemblance to real persons, living or dead, is purely coincidental. The dataset and bot responses contain no intentionally real personal data.


### 👉 [Try bot on Telegram](https://t.me/OsintRatBot)

---

## 🚀 Features

- Search by **name**, **phone number**, **email**, **Telegram ID**, or **Telegram username**  
- Uses **Meilisearch** for lightning-fast indexing and querying  
- Automatic **query queueing**: if the database is offline, all user requests are stored and processed once it’s back online  
- Simple **Telegram bot interface** built with [aiogram2.25](https://docs.aiogram.dev/)  
- Optional **admin panel and logging**

---

## 🧠 Architecture Overview

User → Telegram Bot → Meilisearch API → JSON dataset (~100M records)


- **Bot** handles requests, queues queries, and formats responses  
- **Meilisearch** runs as a separate service (not included in this repo)  
- **SQLite** used locally for queue and metadata storage

---

## ⚙️ Requirements

- **Python** 3.10+
- Running instance of **Meilisearch** (configured separately)
  

---

## 🧩 Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/NYXBAM/OsintRat
cd OsintRat
pip install -r requirements.txt
```
🔑 Environment Variables

Create a .env file in the project root based on the example below:

```
BOT_TOKEN=8123
ADMIN_IDS=1,2,3
CLIENT_URL= # URL of your Meilisearch instance
ADMIN_USERNAME= # Telegram @username of the main admin
CHANNEL_USERNAME= #  Telegram channel username
```

🏃 Running the Bot

Ensure Meilisearch is running and accessible via CLIENT_URL, then simply start the bot:

``` bash 
python main.py

```


# ⚠️ Notes

The actual dataset (~200 GB) is not included.
Use your own JSON data and index it separately in Meilisearch.

Memory usage scales roughly ~1 GB RAM per 1M documents, depending on record complexity.

This project is primarily a technical demo for testing Meilisearch performance at scale.
