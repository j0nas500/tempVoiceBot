import discord
from discord import bot
from discord.ext import commands

from src.db.DbConnection import DbConnection
from src.db.DbTables import DbTables
from src.db.dbQueries import insertIntoVoiceChannels, getTupelById, updateById


class TempVoice(commands.Cog):
    def __init__(self, bot: commands.Bot, db_connection: DbConnection):
        self.bot = bot
        self.db_connection = db_connection

    @commands.slash_command(name="setup", description="Setup for temp voice channels")
    @discord.default_permissions(administrator=True)
    async def setup(
            self,
            ctx,
            voice_channel: discord.Option(discord.VoiceChannel, name="voicechannel",
                                          description="Select the voice channel to join, for a temporary channel"),
            user_limit: discord.Option(discord.SlashCommandOptionType.integer, required=False, max_value=99,
                                       min_value=1,
                                       description="Defines the user limit, if not set it will be unlimited",
                                       name="userlimit",
                                       default=0),
            bitrate: discord.Option(discord.SlashCommandOptionType.integer,
                                    description="Bitrate in kbps of the temp voice channels",
                                    max_value=384,
                                    min_value=8,
                                    default=64),

    ):
        channel: discord.VoiceChannel = voice_channel

        if (bitrate * 1000) > channel.guild.bitrate_limit:
            await ctx.respond(f"Your Server can only have a max Bitrate of {int(channel.guild.bitrate_limit / 1000)}")
            return

        sql = insertIntoVoiceChannels(channel.id, channel.guild.id, False, user_limit, bitrate * 1000)
        execution = self.db_connection.execute(sql)
        if execution is None:
            embed = discord.Embed(
                description=f"Voice channel {channel.mention} set up as a temporary voice channel with the following settings:", )
            embed.add_field(name="User Limit", value=user_limit)
            embed.add_field(name="Bitrate", value=bitrate)
            print(f"New Temporary Voice Channel {channel.name}")
            await ctx.respond("Voice Temp Setup success")
            await ctx.send(embed=embed)
            return
        if execution.startswith("Duplicate entry"):
            await ctx.respond(f"{channel.mention} is already a set up temporary voice channel")

    @commands.slash_command(name="auto_rename", description="Toggles auto rename for your voice Channel")
    @discord.default_permissions(
        connect=True
    )
    async def auto_rename(
            self,
            ctx,
    ):
        member: discord.Member = ctx.author

        if member.voice is None:
            await ctx.respond("You are not in a voice Channel")
            return

        channel: discord.VoiceChannel = member.voice.channel

        result = self.db_connection.execute_list(getTupelById(DbTables.VOICE, channel.id, True))
        if len(result) < 1:
            await ctx.respond("Your are not in a temporary voice Channel")
            return
        if result[0][5] != member.id:
            await ctx.respond("Your are not the owner of the temporary voice Channel")
            return

        if int(result[0][6]) > 0:
            sql = updateById(DbTables.VOICE, channel.id, "auto_rename", False)
            self.db_connection.execute(sql)
            await ctx.respond(f"auto rename for voice channel {channel.mention} disabled")
            return

        sql = updateById(DbTables.VOICE, channel.id, "auto_rename", True)
        self.db_connection.execute(sql)
        await ctx.respond(f"auto rename for voice channel {channel.mention} enabled")

    @commands.slash_command(name="ban", description="Ban/Unban Member from your temp Voice")
    @discord.default_permissions(
        connect=True,
        manage_permissions=True
    )
    async def ban(
            self,
            ctx,
            member_to_kick: discord.Option(discord.SlashCommandOptionType.user, name="user",
                                           description="Select Member to Ban/Unban")
    ):
        member: discord.Member = ctx.author
        member_kick: discord.Member = member_to_kick

        if member == member_kick:
            await ctx.respond("You can't ban yourself")
            return

        if member.voice is None:
            await ctx.respond("You are not in a voice Channel")
            return

        channel: discord.VoiceChannel = member.voice.channel

        result = self.db_connection.execute_list(getTupelById(DbTables.VOICE, channel.id, True))
        if len(result) < 1:
            await ctx.respond("Your are not in a temporary voice Channel")
            return
        if result[0][5] != member.id:
            await ctx.respond("Your are not the owner of the temporary voice Channel")
            return

        if channel.permissions_for(member_kick).connect:
            overwrite = discord.PermissionOverwrite()
            overwrite.connect = False
            await channel.set_permissions(member_kick,
                                          reason=f"{member.name} banned {member_kick.name} to temp voice {channel.name}",
                                          overwrite=overwrite)
            if member_kick.voice is not None and member_kick.voice.channel == channel:
                await member_kick.move_to(None)
            print(f"{member.name} banned {member_kick.name} to temp voice {channel.name}")
            await ctx.respond(f"{member_kick.mention} banned from voice {channel.mention}")
            return

        overwrite = discord.PermissionOverwrite()
        overwrite.connect = None
        await channel.set_permissions(member_kick,
                                      reason=f"{member.name} unbanned {member_kick.name} to temp voice {channel.name}",
                                      overwrite=overwrite)
        print(f"{member.name} unbanned {member_kick.name} to temp voice {channel.name}")
        await ctx.respond(f"{member_kick.mention} unbanned from voice {channel.mention}")
        return
