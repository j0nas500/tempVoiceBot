import logging
import os
import dotenv

from src.EventsListener import EventsListener
from src.commands.voice.TempVoice import TempVoice
from src.db.DbConnection import DbConnection
from src.db.dbQueries import createTableGuilds, createTableVoiceChannels

dotenv.load_dotenv()
logging.basicConfig()
db_connection = DbConnection(
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        host=os.getenv("MYSQL_HOST"),
        port=int(os.getenv("MYSQL_PORT")),
        database=os.getenv("MYSQL_DATABASE")
)
db_connection.execute(createTableGuilds())
db_connection.execute(createTableVoiceChannels())


# intents = discord.Intents.default()
# intents.presences = True
# intents.members = True
# intents.message_content = True

bot = EventsListener(db_connection=db_connection)
bot.add_cog(TempVoice(bot=bot, db_connection=db_connection))
bot.run(os.getenv("TOKEN"))
