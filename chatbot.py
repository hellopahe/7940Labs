from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters,CallbackContext
import configparser
import logging
import redis
import requests
import json
global redis1

import os


def main():
    # Load your token and create an Updater for your Bot
    # config = configparser.ConfigParser()
    # config.read('config.ini')
    updater = Updater(token=(os.environ['ACCESS_TOKEN']), use_context=True)
    dispatcher = updater.dispatcher
    global redis1
    redis1 = redis.Redis(host=(os.environ['HOST']), password=
    (os.environ['PASSWORD']), port=(os.environ['REDISPORT']))
    # You can set this logging module, so you will know when and why things do notwork as expected
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    # register a dispatcher to handle message: here we register an echo dispatcher
    echo_handler = MessageHandler(Filters.text & (~Filters.command), echo)
    dispatcher.add_handler(echo_handler)
    # on different commands - answer in Telegram
    dispatcher.add_handler(CommandHandler("add", add))
    dispatcher.add_handler(CommandHandler("help", help_command))

    # writeup on FEB 14 2023
    dispatcher.add_handler(CommandHandler('hello', hello))

    # add up functions
    dispatcher.add_handler(CommandHandler('ask', ask))

    # To start the bot:
    updater.start_polling()
    updater.idle()

def ask(update: Update, msg: CallbackContext):
    url = "https://chatgpt-api.shn.hk/v1/"
    headers = {"Content-Type": "application/json",
               "User-Agent": "PostmanRuntime/7.31.3"
               }
    data = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": msg.args[0]}]
    }
    response = requests.post(url, headers=headers, data=json.dumps(data))
    result = json.loads(response.content.strip())
    rply = result['choices'][0]['message']['content']

    logging.info("Ask: " + msg.args[0])
    logging.info("GPT: " + rply)
    update.message.reply_text(str(rply))
    # update.message.reply_text(str('Good day, ' + rply + '!'))

def hello(update: Update, msg: CallbackContext):
    logging.info(msg.args[0])
    update.message.reply_text(str('Good day, ' + msg.args[0] + '!'))


def echo(update, context):
    reply_message = update.message.text.upper()
    logging.info("Update: " + str(update))
    logging.info("context: " + str(context))
    context.bot.send_message(chat_id=update.effective_chat.id, text= reply_message)


# Define a few command handlers. These usually take the two arguments update and
# context. Error handlers also receive the raised TelegramError object in error.
def help_command(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /help is issued."""
    update.message.reply_text('Helping you helping you.')


def add(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /add is issued."""
    try:
        global redis1
        logging.info(context.args[0])
        msg = context.args[0] # /add keyword <-- this should store the keyword
        redis1.incr(msg)
        update.message.reply_text('You have said ' + msg + ' for ' + redis1.get(msg).decode('UTF-8') + ' times.')
    except (IndexError, ValueError):
        update.message.reply_text('Usage: /add <keyword>')


if __name__ == '__main__':
    main()
