import discord
from discord import bot
from discord.ext import commands

from src.db.DbConnection import DbConnection
from src.db.DbTables import DbTables
from src.db.dbQueries import insertIntoVoiceChannels, getTupelById, updateById


class GameRoles(commands.Cog):
    def __init__(self, bot: commands.Bot, db_connection: DbConnection):
        self.bot = bot
        self.db_connection = db_connection

    @commands.slash_command(name="game_role", description="Add/Remove a Game Role")
    @discord.default_permissions(administrator=True)
    async def enable(
            self,
            ctx,
            game_role: discord.Option(discord.SlashCommandOptionType.role, description="Role to be assigned to one"),
            activity: discord.Option(discord.SlashCommandOptionType.string, description="For which activity/game the role should be assigned")

    ):
        await ctx.respond(f"is already a set up temporary voice channel")


