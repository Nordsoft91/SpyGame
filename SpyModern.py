import logging
import random
import json
import subprocess
from typing import Type
from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, Update, ParseMode, parsemode, InlineKeyboardButton, TelegramError
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, dispatcher, ConversationHandler, CallbackContext, CallbackQueryHandler
from telegram.messageentity import MessageEntity
from decouple import config

loggingFilename = 'logging.log'
logging.basicConfig(filename=loggingFilename, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

SETTINGS_ENTRY, SETTINGS_PLAYER, SETTINGS_PRESET, SETTINGS_PLACE, SETTINGS_PRESET_NEW, GAME_ENTRY, GAME_JOIN, GAME_WAIT = range(8)

sessions = {}

#read last lines from log file
def getLogging(n) -> list:
    a_file = open(loggingFilename, "r")
    lines = a_file.readlines()
    last_lines = lines[-n:]
    a_file.close()
    return last_lines

#class to store game
class session:
    count = 0 #amount of players in game
    players = [] #players nicknames
    chats = [] #players chat ids
    places = [] #list of places
    
    spy = 0
    place = ''

    def init(self) -> None:
        self.spy = random.randint(1,self.count)
        self.place = random.choice(self.places)
        logging.info(f"Session init. Place {self.place}")

    #show information about game
    def description(self) -> str:
        return f"Игроки {len(self.players)}/{self.count}\n    {self.players}\n\nМеста: {self.places}\n/status - обновить"

#===SYSTEM===
def system(update, context):
    #check password
    u = update.effective_user.name
    sudo = False
    try:
        pswd = context.args[0]
    except (IndexError, ValueError):
        update.message.reply_text('Forbidden')
        logging.error(f"{u} system called without password")
        return

    if pswd not in [config("ADMIN"), config("ROOT")]:
        logging.warning(f"{u} system called with wrong password: {pswd}")
        update.message.reply_text('Wrong password')

    if pswd == config("ROOT"):
        sudo = True

    try:
        key = context.args[1]
    except (IndexError, ValueError):
        logging.warning("{u} system called without key")
        key = 'help'

    #generate system info
    global sessions
    s = f"SYSTEM\nchat_id:{update.effective_chat.id}\nname:{update.effective_user.name}\n"

    if key == 'bot':
        for k in context.bot_data.keys():
            s += f"{k}: {context.bot_data[k]}\n"
        if sudo:
            for udata in context._user_id_and_data:
                s += str(udata) + '\n'
                #for k in context._user_id_and_data[udata].keys():
                #s += f"user {udata}, {k}: {context._user_id_and_data[udata][k]}\n"

    if key == 'user':
        for k in context.user_data.keys():
            s += f"{k}: {context.user_data[k]}\n"

    if key == 'sessions':
        for k in sessions.keys():
            ses = sessions[k]
            s += f"\n{k}:\n count: {ses.count}\n players: {ses.players}\n chats: {ses.chats}\n places: {ses.chats}\n spy: {ses.spy}\n place: {ses.place}"

    if key == 'places':
        with open("places.json", "r") as read_file:
            data = json.load(read_file)
        for k in data.keys():
            s += f"{k}: {data[k]}\n"

    if key == 'generator':
        s += "int 1-5 genertor: "
        for k in [1,2,3,4,5,6,7,8,9,10]:
            s += f"{random.randint(1,5)} "
        s += "\nrandom element generator (a-e): "
        test = ['a','b','c','d','e']
        for k in [1,2,3,4,5,6,7,8,9,10]:
            s += f"{random.choice(test)} "

    if key == 'clear':
        if not sudo:
            s += "Need superuser permissions"
        else:
            sessions = {}
            s += "System variables have been cleaned up"

    if key == 'reset':
        if not sudo:
            s += "Need superuser permissions"
        else:
            sessions.clear()
            context._user_id_and_data = tuple()
            context.dispatcher.handlers[1][0]._conversations.clear()
            with open(loggingFilename, 'w'):
                pass
            s += "System reset done"

    if key == 'log':
        n = 20
        if sudo:
            n = 100
        logs = getLogging(n)
        s += ''.join(logs)

            
    if key == 'help':
        s += "/system pswd key\n - bot\n - user\n - sessions\n - help\n - places\n - generator\n - clear\n - reset\n - log"

    logging.info(f"{u} system called normally with key {key}")
    update.message.reply_text(s)

#===ERROR DISPATCHER===
def error(update, context):
    if update:
        logging.error(f"{update.effective_user.name} error called")
    else:
        logging.error("NoneType udpate error function")
    update.message.reply_text('Ошибка. Введите /start чтобы перезагрузить бота.')


#===COMMAND===
def start(update, context):
    logging.info(f"{update.effective_user.name} start called")
    #initialize player
    context.user_data['players'] = 4
    context.user_data['preset'] = 'basic'
    context.user_data['host'] = 0
    context.user_data['game'] = 0
    #kick off from all sessions
    sessionsForDel = []
    for ses in sessions.keys():
        if update.effective_user.name in sessions[ses].players:
            sessions[ses].players.remove(update.effective_user.name)
            sessions[ses].chats.remove(update.effective_chat.id)
            #notify other players
            for notification in sessions[ses].chats:
                try:
                    context.bot.send_message(notification, f"{update.effective_user.name} покинул игру")
                except (TelegramError):
                    pass
            if not sessions[ses].players:
                sessionsForDel.append(ses)
    for ses in sessionsForDel:
        del sessions[ses]
    
    reply_keyboard = [['/help', '/game', '/settings']]
    update.message.reply_text(
        """
        <b>Добро пожаловать в игру шпион</b>
        <a>Список доступных команд
        /help вывести список команд
        /game начать игру
        /settings настройки
        Настройки количества игроков и настройки мест будут применены только для новых сессий.</a>
        """,
        parse_mode=ParseMode.HTML,
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=True, input_field_placeholder='main menu'),
        )


#===COMMAND===
def help(update, context):
    logging.info(f"{update.effective_user.name} help called")
    s = "Помощь\n"
    if 'game' not in context.user_data:
        s += "Бот не инициализирован. При дальнейшей отправке команд возможны ошибки"
    update.message.reply_text(s)


#===COMMAND===
def game(update, context) -> int:
    logging.info(f"{update.effective_user.name} game called")
    try:
        players = context.user_data['players']
        preset = context.user_data['preset']
    except (KeyError, IndexError, ValueError):
        update.message.reply_text('Ошибка. Введите /start чтобы перезагрузить бота.')
        return ConversationHandler.END
    
    with open("places.json", "r") as read_file:
            data = json.load(read_file)

    s = f"""
        Настройки:
            Игроков: {players}
            Места: {preset} {data[preset]}
        """
    keyboard = [[InlineKeyboardButton("Создать игру", callback_data='host'),
                 InlineKeyboardButton("Присоединиться", callback_data='join')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(s, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

    return GAME_ENTRY


#===CALLBACK===
def gameCallback(update, context) -> int:
    logging.info(f"{update.effective_user.name} gameCallback called")
    global sessions
    query = update.callback_query
    query.answer()

    if query.data == 'host':
        #1. if game was already created
        if context.user_data['host'] in sessions.keys():
            query.message.reply_text(f"Вы уже создали игру ранее PIN {context.user_data['host']}\nВведите /status чтобы обновить состояние игры")
            return GAME_WAIT

        #2. if already in the game
        if context.user_data['game'] in sessions.keys():
            #2a. remove myself from game
            sessions[context.user_data['game']].players.remove(update.effective_user.name)
            sessions[context.user_data['game']].chats.remove(update.effective_chat.id)
            #2b. notify other players
            for notification in sessions[context.user_data['game']].chats:
                try:
                    context.bot.send_message(notification, f"{update.effective_user.name} покинул игру")
                except (TelegramError):
                    pass
            #2c. cleanup
            if len(sessions[context.user_data['game']].players) == 0:
                query.message.reply_text(f"Игра {context.user_data['game']} удалена")
                del sessions[context.user_data['game']]
            else:
                query.message.reply_text(f"Вы покинули игру {context.user_data['game']}")
            context.user_data['game'] = 0
            

        #3. create game
        #3a. read places from file
        with open("places.json", "r") as read_file:
            data = json.load(read_file)

        #3b. generate unique pin code
        pin = random.randint(1000,9999)
        while pin in sessions.keys():
            pin = random.randint(1000,9999)

        #3c. create new game session
        sessions[pin] = session()
        sessions[pin].count = context.user_data['players']
        sessions[pin].players.append(update.effective_user.name)
        sessions[pin].chats.append(update.effective_chat.id)
        sessions[pin].places = data[context.user_data['preset']]
        sessions[pin].init()

        #3d. join to the new game
        query.message.reply_text(f"Создана новая игра. PIN {pin}\nВведите /status чтобы обновить состояние игры")
        context.user_data['host'] = pin
        context.user_data['game'] = pin
        
        return GAME_WAIT

    elif query.data == 'join':
        query.message.reply_text(f"Введите PIN")
        return GAME_JOIN


#===MESSAGE===
def expectPin(update, context) -> int:
    logging.info(f"{update.effective_user.name} expectPin called {update.message.text}")
    global sessions
    try:
        pin = int(update.message.text)   

    except (KeyError, IndexError, ValueError):
        return GAME_JOIN

    #1. if player if the host of this game
    if pin == context.user_data['host']:
        update.message.reply_text(f"Вы не можете присоединиться к своей игре. Вы уже в ней.")
        return GAME_WAIT

    #2. if pin is not found
    if pin not in sessions.keys():
        update.message.reply_text(f"Игра не найдена")
        return GAME_JOIN
    
    #3. if cannot join due to limit on players count
    if len(sessions[pin].players) >= sessions[pin].count:
        update.message.reply_text(f"Игра уже началась")
        return GAME_JOIN

    #4. detach from other game
    if context.user_data['game'] in sessions.keys():
        #4a. remove myself from game
        sessions[context.user_data['game']].players.remove(update.effective_user.name)
        sessions[context.user_data['game']].chats.remove(update.effective_chat.id)
        #4b. notify other players
        for notification in sessions[context.user_data['game']].chats:
            try:
                context.bot.send_message(notification, f"{update.effective_user.name} покинул игру")
            except (TelegramError):
                pass
        #4c. cleanup
        if len(sessions[context.user_data['game']].players) == 0:
            update.message.reply_text(f"Игра {context.user_data['game']} удалена")
            del sessions[context.user_data['game']]
        else:
            update.message.reply_text(f"Вы покинули игру {context.user_data['game']}")
        context.user_data['game'] = 0

    #5. delete previousle created host game
    if context.user_data['host'] in sessions.keys():
        #5a. notify other players
        #    message will not be sent to myself because I was detached from the game in item 4
        for notification in sessions[context.user_data['host']].chats:
            try:
                context.bot.send_message(notification, f"Игра удалена, так как {update.effective_user.name} покинул игру")
            except (TelegramError):
                pass
        #5b. remove game session and cleanup
        del sessions[context.user_data['host']]
        update.message.reply_text(f"Ранее созданная вами игра {context.user_data['host']} удалена")
        context.user_data['host'] = 0
        
    #6. send notification to other players that you have joined
    for notification in sessions[pin].chats:
        try:
            context.bot.send_message(notification, f"{update.effective_user.name} присоединился к игре")
        except (TelegramError):
            pass

    #7. join to the game
    sessions[pin].players.append(update.effective_user.name)
    sessions[pin].chats.append(update.effective_chat.id)

    context.user_data['game'] = pin
    update.message.reply_text(f"Вы присоединились к игре.\n{sessions[pin].description()}")

    #7. wait for other players
    if len(sessions[pin].players) < sessions[pin].count:
        return GAME_WAIT

    #8. start game
    spyPlayerChat = sessions[pin].chats[sessions[pin].spy]
    for notification in sessions[pin].chats:
        try:
            if notification == spyPlayerChat:
                context.bot.send_message(notification, f"ТЫ ШПИОН")
            else:
                context.bot.send_message(notification, f"МЕСТО: {sessions[pin].place}")
        except (TelegramError):
            pass
    return ConversationHandler.END
    



#===COMMAND===
def status(update, context) -> int:
    logging.info(f"{update.effective_user.name} status called")
    global sessions
    try:
        pin = context.user_data['game']
    except (KeyError, IndexError, ValueError):
        update.message.reply_text('Ошибка. Введите /start чтобы перезагрузить бота.')
        return ConversationHandler.END

    if pin not in sessions.keys():
        update.message.reply_text(f"Игра завершена")
        return GAME_ENTRY

    update.message.reply_text(sessions[pin].description())

#===COMMAND===
def settings(update, context) -> int:
    logging.info(f"{update.effective_user.name} settings called")
    try:
        players = context.user_data['players']
        preset = context.user_data['preset']
    except (IndexError, ValueError):
        update.message.reply_text('Ошибка. Введите /start чтобы перезагрузить бота.')
        return ConversationHandler.END

    try:
        with open("places.json", "r") as read_file:
            data = json.load(read_file)

        keyboard = [[InlineKeyboardButton("Players", callback_data='player')],
                    [InlineKeyboardButton("Preset", callback_data='preset')],
                    [InlineKeyboardButton("Create", callback_data='place')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        s = f"""
        Настройки:
            Игроков: {players}
            Места: {preset} {data[preset]}
        Players - настроить количество игроков
        Preset - выбрать список мест
        Place - добавить или удалить место
        """
        context.bot.send_message(update.effective_chat.id, s, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
    except (AttributeError, TypeError, TelegramError):
        pass

    return SETTINGS_ENTRY


#===CALLBACK===
def settingsCallback(update, context) -> int:
    logging.info(f"{update.effective_user.name} settingsCallback called")
    query = update.callback_query
    query.answer()

    if query.data == 'player':
        query.message.reply_text("Укажите количество игроков")
        return SETTINGS_PLAYER

    elif query.data == 'preset':
        keyboard = [[InlineKeyboardButton("Создать", callback_data='preset_create'), 
                    InlineKeyboardButton(f"Удалить {context.user_data['preset']}", callback_data='preset_remove')]]
        with open("places.json", "r") as read_file:
            data = json.load(read_file)
        for preset in data.keys():
            keyboard.append([InlineKeyboardButton(preset, callback_data=f'preset_switch%{preset}')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.message.reply_text("Выберите список мест или создайте новый", reply_markup=reply_markup)
        return SETTINGS_PRESET

    elif query.data == 'place':
        query.message.reply_text("Введите место для создания или удаления")
        return SETTINGS_PLACE
    

#===CALLBACK===
def presetCallback(update, context) -> int:
    logging.info(f"{update.effective_user.name} presetCallback called")
    query = update.callback_query
    query.answer()

    if query.data == 'preset_create':
        query.message.reply_text("Введите название нового списка мест")
        return SETTINGS_PRESET_NEW

    elif query.data == 'preset_remove':
        if context.user_data['preset'] == 'basic':
            query.message.reply_text("Базовый список мест нельзя удалить")
            return settings(update, context)
        with open("places.json", "r") as read_file:
            data = json.load(read_file)
        del data[context.user_data['preset']]
        with open("places.json", "w") as write_file:
            json.dump(data, write_file, indent=4)
        query.message.reply_text(f"Список {context.user_data['preset']} удален")
        context.user_data['preset'] = 'basic'
        return settings(update, context)

    else:

        rhs = query.data.split("%")
        if len(rhs) == 2:
            context.user_data['preset'] = rhs[1]
        return settings(update, context)
        


#===MESSAGE===
def expectPreset(update, context) -> int:
    logging.info(f"{update.effective_user.name} expectPreset called {update.message.text}")
    with open("places.json", "r") as read_file:
        data = json.load(read_file)
        
    data[update.message.text] = []
    
    with open("places.json", "w") as write_file:
        json.dump(data, write_file, indent=4)

    context.user_data['preset'] = update.message.text

    return settings(update, context)


#===MESSAGE===
def expectPlayers(update, context) -> int:
    logging.info(f"{update.effective_user.name} expectPlayers called {update.message.text}")
    try:
        players = int(update.message.text)   

    except (IndexError, ValueError):
        return SETTINGS_PLAYER

    context.user_data['players'] = players

    return settings(update, context)


#===MESSAGE===
def expectPlace(update, context) -> int:
    pls = update.message.text
    logging.info(f"{update.effective_user.name} expectPlace called {pls}")

    if pls[0] == '/':
        return ConversationHandler.END

    with open("places.json", "r") as read_file:
        data = json.load(read_file)
    
    if pls in data[context.user_data['preset']]:
        data[context.user_data['preset']].remove(pls)
        update.message.reply_text(f"Удалено\n{data[context.user_data['preset']]}")
    else:
        data[context.user_data['preset']].append(pls)
        update.message.reply_text(f"Добавлено\n{data[context.user_data['preset']]}")
    
    with open("places.json", "w") as write_file:
        json.dump(data, write_file, indent=4)

    return SETTINGS_PLACE


#===MAIN===
def main():
    TOKEN = config("TOKEN")

    updater = Updater(TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    settingsHandler = CommandHandler('settings', settings)
    gameHandler = CommandHandler('game', game)

    dispatcher.add_error_handler(error)

    dispatcher.add_handler(CommandHandler("start", start), 0)
    dispatcher.add_handler(CommandHandler("help", help), 0)
    dispatcher.add_handler(CommandHandler("system", system), 0)

    #settings
    settingsCallbackHandler = CallbackQueryHandler(settingsCallback)
    conv_create_handler = ConversationHandler(
        entry_points=[settingsHandler, gameHandler],
        states={
            SETTINGS_ENTRY: [settingsCallbackHandler],
            SETTINGS_PLAYER: [MessageHandler(Filters.text, expectPlayers), settingsCallbackHandler],
            SETTINGS_PRESET: [CallbackQueryHandler(presetCallback)],
            SETTINGS_PRESET_NEW: [MessageHandler(Filters.text, expectPreset)],
            SETTINGS_PLACE: [MessageHandler(Filters.text, expectPlace), settingsCallbackHandler],
            GAME_ENTRY: [CallbackQueryHandler(gameCallback), CommandHandler('status', status)],
            GAME_JOIN: [MessageHandler(Filters.text, expectPin)],
            GAME_WAIT: [CommandHandler('status', status)]
        },
        fallbacks=[], allow_reentry=True,
        map_to_parent={
        }
    )
    dispatcher.add_handler(conv_create_handler, 1)

    updater.start_polling()

    updater.idle()



if __name__ == '__main__':
    main()  