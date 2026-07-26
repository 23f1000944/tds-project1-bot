import telebot
import os
bot = telebot.TeleBot(os.environ['TELEGRAM_TOKEN'])
print(bot.get_me())
