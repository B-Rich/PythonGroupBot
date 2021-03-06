from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
import logging
import requests
import generated_dict
import dizdb
import html

info = dizdb.load("info.db")

db = dizdb.load(info.show()["database"])
textsdb = dizdb.load(info.show()["translations"])

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


def translate(msg, target):
    url = "https://translation.googleapis.com/language/translate/v2"
    result = requests.get(url, params={
        "target": target,
        "q": msg,
        "key": info.show()["google_token"]
    }).json()
    lang = result["data"]["translations"][0]["translatedText"]
    r_lang = html.unescape(lang)
    return(r_lang)

def detect(msg):
    """Do an HTTP GET to detect a string's language.

    Using Google Translate API.
    """
    url = "https://translation.googleapis.com/language/translate/v2/detect"
    result = requests.get(url, params={
        "q": msg,
        "key": info.show()["google_token"]
    }).json()
    lang = result["data"]["detections"][0][0]["language"]
    return(generated_dict.codes[lang])

def button(bot, update):
    query = update.callback_query
    ID = query["id"]
    text = query["message"]["text"]
    lang = text.split()[5][:-1]
    translated_ = textsdb.get(lang)

    bot.answerCallbackQuery(ID,
                            text=translated_,
                            show_alert=True)

def get_admin_ids(bot, chat_id):
    return [admin.user.id for admin in bot.getChatAdministrators(chat_id)]

def echo(bot, update):
    DETECT_META = None
    database = db.show()
    if update.message and str(update.message.chat.id) in info.show()["allowed_groups"]:
        message = update.message
        id_ = message["message_id"]
        text = message["text"]
        detected_lang = detect(text).split()
        for lang, username in database.items():
            if detected_lang[0] == lang:
                DETECT_META = False
                if len(username) >= 2:
                    txt = "I've detected that you speak {}. You should join {}".format(lang, " or ".join(username))
                else:
                    txt = "I've detected that you speak {}. You should join {}".format(lang, username[0])
                keyboard = [[InlineKeyboardButton("Read in {}".format(lang), callback_data="1")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                bot.sendMessage(
                    chat_id=update.message.chat.id,
                    text=txt,
                    reply_to_message_id=int(id_),
                    reply_markup=reply_markup
                    )
                if len(text) > int(info.show()["message_max_char"]) and update.message.chat.id not in get_admin_ids(bot, update.message.chat.id):
                    update.message.bot.delete_message(
                        chat_id=update.message.chat.id,
                        message_id=id_
                        )
            else:
                DETECT_META = True

        if DETECT_META is True:
            if "anyone" in text and not "how" in text:
                update.message.reply_text("Meta test.")

def new(bot, update):
    """Add groups to a language key"""
    if update.message.from_user.id in get_admin_ids(bot, update.message.chat.id) and str(update.message.chat.id) in info.show()["allowed_groups"]:
        if update.message:
            text = update.message["text"]
            text = text.split()
            if len(text) >= 3:
                key = text[1].lower()
                key1 = key[0].upper() + key[1:]
                groups_ = " ".join(text[2:])
                db.lappend(key1, groups_)
                db.write()
            else:
                update.message.reply_text(
                    "You have to at least provide a language name and at least one group."
                    )

def group(bot, update):
    """Returns a list of groups based on the provided language"""
    # Sorry PEP8
    if update.message or update.message.reply_to_message and str(update.message.chat.id) in info.show()["allowed_groups"]:
        text = update.message["text"]
        text = text.split()
        if len(text) >= 2:
            key = text[1].lower()
            key1 = key[0].upper() + key[1:]
            result = " ".join(db.get(key1))
            update.message.reply_text("Group(s) for {}: {}".format(key1, result))
        else:
            update.message.reply_text(
                "You have to provide a language name."
            )

def _error(bot, update, error):
    """Log errors."""
    logger.warn('Update "%s" caused error "%s"' % (update, error))

def groups(bot, update):
    """Returns the content of the database file"""
    if update.message.from_user.id in get_admin_ids(bot, update.message.chat.id):
        if update.message:
            r_file = open(info.show()["database"], "r+")
            text = """
<b>File</b>: <code>groups.db</code>
<b>KVS (database)</b>: <a href="https://github.com/dizaztor/dizDB">dizDB</a>
<b>Content</b>: <code>
{}</code>
""".format(r_file.read())
            update.message.reply_text(text, parse_mode="HTML", disable_web_page_preview=True)

def main():
    """main function?"""
    updater = Updater(info.show()["bot_token"])

    dp = updater.dispatcher

    dp.add_handler(CommandHandler("new", new))
    dp.add_handler(CommandHandler("group", group))
    dp.add_handler(CommandHandler("groups", groups))
    dp.add_handler(MessageHandler(Filters.text, echo))
    dp.add_handler(CallbackQueryHandler(button))
    dp.add_error_handler(_error)

    updater.start_polling()

    updater.idle()


if __name__ == '__main__':
    main()
