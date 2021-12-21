# Spy Game
## Introduction
This is code of Telegram bot, which can help to play on Spy game.

You can play in this game using my bot: https://t.me/SpyGameForFunBot or deploy it on your own!

Note that I use my old raspPi as a server for this bot and it not always work :)

## Game Rules
 - Each player is either spy or not.
 - Each player knows if he or she spy or not, but doesn't know anything about others.
 - There is one location, randomly selected by game.
 - Spy doesn't know location, other players know
 - Spy goal: figure out location
 - Other players' goal: discover the spy
 - Player asks question about location any other player
 - Question assumes yes or no answer

## Installation

1. You need to create bot which will be used to access to your game.
This bot will be controlled by this program.
To control your bot you have to know bot unique `TOKEN`.
Guide on how to create telegram bot and obtain token is here: https://core.telegram.org/bots
In few words, you need to:
   1. Open BotFather bot https://t.me/BotFather
   2. Start bot by command **/start**
   3. Create new bot by command **/newbot** and follow instructions
   4. Use your token received from BotFather in step below

2. Create file named `.env` in bot directory with following content:
```
TOKEN = 'your private telegram bot token'
ADMIN = 'password used to bot admin commands'
ROOT = 'password used to bot root commands'
```

3. Install all dependencies for this program
```
pip install requrements.txt
```

3. Run bot server
```
python3 SpyModern.py
```
