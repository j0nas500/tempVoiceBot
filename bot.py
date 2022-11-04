import logging
import os
from collections import Counter

import discord
import dotenv
import mariadb

from dbQueries import *

dotenv.load_dotenv()
bot = discord.Bot(intents=discord.Intents.all())
logging.basicConfig()

try:
    conn = mariadb.connect(
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        host=os.getenv("MYSQL_HOST"),
        port=int(os.getenv("MYSQL_PORT")),
        database=os.getenv("MYSQL_DATABASE")
    )
    cursor = conn.cursor()

    print("Connected to the Database")
except mariadb.Error as e:
    print("Error at:")
    print(e)
    exit()


def execute(query):
    try:
        cursor.execute(query)
        conn.commit()
        # cursor.fetchall()
    except mariadb.Error as e:
        print(f"Error: {e}")
        return str(e)


def execute_list(query):
    try:
        cursor.execute(query)
        conn.commit()
        return cursor.fetchall()
    except mariadb.Error as e:
        print(f"Error: {e}")
        return str(e)


def execute_rows(query):
    try:
        cursor.execute(query)
        rows = cursor.rowcount
        conn.commit()
        return rows
    except mariadb.Error as e:
        print(f"Error: {e}")
        return str(e)


execute(createTableGuilds())
execute(createTableVoiceChannels())


@bot.event
async def on_ready():
    print(f"{bot.user} is ready and online!")


# @bot.event
# async def on_error(ctx, error):
#     print("asdasd")
#     if isinstance(error, discord.HTTPException):
#         print("DASDHASDHAJKSHDJKASHDKJ")
#         await ctx.send("You are ratelimited")

# @Client.event
# async def on_command_error(ctx, error):
#     if isinstance(error, discord.HTTPException):
#         print("DASDHASDHAJKSHDJKASHDKJ")
#         await ctx.send("You are ratelimited")


@bot.event
async def on_guild_join(guild: discord.Guild):
    print(f"{bot.user} joined {guild.name}")
    sql = insertIntoGuilds(guild.id, int(guild.bitrate_limit))
    execute(sql)


@bot.event
async def on_guild_remove(guild: discord.Guild):
    print(f"{bot.user} leaved {guild.name}")
    sql = deleteTupelById(DbTables.GUILDS, guild.id)
    execute(sql)


@bot.event
async def on_guild_update(guild_old: discord.Guild, guild_new: discord.Guild):
    if guild_old.bitrate_limit == guild_new.bitrate_limit:
        return
    print(f"{guild_new.name} Bitrate has changed to {guild_new.bitrate_limit}")
    sql = updateById(DbTables.GUILDS, guild_new.id, "bitrate_limit", guild_new.bitrate_limit)
    execute(sql)


@bot.event
async def on_guild_channel_delete(channel):
    sql = deleteTupelById(DbTables.VOICE, channel.id)
    result = execute_rows(sql)
    if result > 0:
        print(f"Temporary Voice Channel {channel.id} removed")


@bot.event
async def on_voice_state_update(member: discord.Member, voice_state_old: discord.VoiceState,
                                voice_state_new: discord.VoiceState):
    channel_new: discord.VoiceChannel = voice_state_new.channel
    channel_old: discord.VoiceChannel = voice_state_old.channel

    if channel_new is not None:
        sql = getTupelById(DbTables.VOICE, channel_new.id, False)
        result = execute_list(sql)
        if len(result) > 0:
            channel_name = None
            for x in member.activities:
                if x.type is discord.ActivityType.playing:
                    channel_name = x.name
                    break

            if channel_name is None:
                channel_name = member.name

            tmp_channel = await member.guild.create_voice_channel(
                name=channel_name,
                user_limit=int(result[0][2]),
                bitrate=int(result[0][3]),
                reason=f"{member.name} joined temp Voice {channel_new.name}",
                position=channel_new.position,
                category=channel_new.category
            )
            sql = insertIntoVoiceChannels(tmp_channel.id, tmp_channel.guild.id, True, owner_id=member.id)
            execute(sql)
            await member.move_to(channel=tmp_channel, reason="{member.name} joined temp Voice {channel_new.name}")
            overwrite = discord.PermissionOverwrite()
            overwrite.manage_channels = True
            overwrite.manage_permissions = True
            await tmp_channel.set_permissions(member, overwrite=overwrite)
            print(f"Temporary Voice Channel {tmp_channel.name} created by {member.name}")

        result = execute_list(getTupelById(DbTables.VOICE, channel_new.id, True))
        if len(result) > 0:
            if int(result[0][6]) < 1:
                return
            member: discord.Member = bot.get_user(int(result[0][5]))
            await update_voice_channel_name(member, channel_new)

    if channel_old is not None:
        result = execute_list(getId(DbTables.VOICE, channel_old.id, True))
        if len(result) > 0:
            if len(channel_old.members) == 0:
                await channel_old.delete(reason="No one in the temp voice channel")
                return

            result = execute_list(getTupelById(DbTables.VOICE, channel_old.id, True))
            if result[0][5] == member.id:
                new_owner = channel_old.members[0]
                sql = updateById(DbTables.VOICE, channel_old.id, "owner_id", new_owner.id)
                overwrite = discord.PermissionOverwrite()
                overwrite.manage_channels = True
                overwrite.manage_permissions = True
                await channel_old.set_permissions(new_owner, overwrite=overwrite)
                overwrite.manage_channels = None
                overwrite.manage_permissions = None
                await channel_old.set_permissions(member, overwrite=overwrite)
                print(f"{new_owner.name} is now the Owner of {channel_old.name} (old Owner: {member.name})")
                execute(sql)
                if int(result[0][6]) < 1:
                    return
                await update_voice_channel_name(new_owner, channel_old)

            if int(result[0][6]) < 1:
                return
            await update_voice_channel_name(discord.Member(bot.get_user(int(result[0][5]))), channel_old)


@bot.event
async def on_presence_update(member_old: discord.Member, member_new: discord.Member):
    if member_new.voice is None:
        return

    channel: discord.VoiceChannel = member_new.voice.channel

    result = execute_list(getTupelById(DbTables.VOICE, channel.id, True))
    if len(result) < 1:
        return
    if int(result[0][6]) < 1:
        return

    member: discord.Member = bot.get_user(int(result[0][5]))
    await update_voice_channel_name(member, channel)


async def update_voice_channel_name(owner: discord.Member, channel: discord.VoiceChannel):

    activities: list = []
    all_member = channel.members
    for x in all_member:
        for y in x.activities:
            if y.type is discord.ActivityType.playing:
                #print(y.name)
                activities.append(y.name)
                break

    if len(activities) < 1:
        if channel.name == owner.name:
            return
        print(f"{channel.name} will be renamed to {owner.name} [0]")
        await channel.edit(name=owner.name)
        return

    counts = dict(Counter(activities))
    highest_value_key = max(counts, key=counts.get)
    highest_value = counts.get(highest_value_key)

    if len(all_member) * 0.5 < highest_value:
        if channel.name == highest_value_key:
            return
        print(f"{channel.name} will be renamed to {highest_value_key} [1]")
        await channel.edit(name=highest_value_key)
        return

    if channel.name == owner.name:
        return
    print(f"{channel.name} will be renamed to {owner.name} [2]")
    await channel.edit(name=owner.name)


@bot.slash_command(name="setup", description="Setup for temp voice channels")
@discord.default_permissions(administrator=True)
async def setup(
        ctx,
        voice_channel: discord.Option(discord.VoiceChannel, name="voicechannel",
                                      description="Select the voice channel to join, for a temporary channel"),
        user_limit: discord.Option(discord.SlashCommandOptionType.integer, required=False, max_value=99, min_value=1,
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
    sql = insertIntoVoiceChannels(channel.id, channel.guild.id, False, user_limit, bitrate * 1000)
    execution = execute(sql)
    if execution is None:
        embed = discord.Embed(
            description=f"Voice channel <#{channel.id}> set up as a temporary voice channel with the following settings:", )
        embed.add_field(name="User Limit", value=user_limit)
        embed.add_field(name="Bitrate", value=bitrate)
        print(f"New Temporary Voice Channel {channel.name}")
        await ctx.respond("A")
        await ctx.send(embed=embed)
        return
    if execution.startswith("Duplicate entry"):
        await ctx.respond(f"<#{channel.id}> is already a set up temporary voice channel")


@bot.slash_command(name="auto_rename", description="Toggles auto rename for your voice Channel")
@discord.default_permissions(
    connect=True
)
async def auto_rename(
        ctx,
):
    member: discord.Member = ctx.author

    if member.voice is None:
        await ctx.respond("You are not in a voice Channel")
        return

    channel: discord.VoiceChannel = member.voice.channel

    result = execute_list(getTupelById(DbTables.VOICE, channel.id, True))
    if len(result) < 1:
        await ctx.respond("Your are not in a temporary voice Channel")
        return
    if result[0][5] != member.id:
        await ctx.respond("Your are not the owner of the temporary voice Channel")
        return

    if int(result[0][6]) > 0:
        sql = updateById(DbTables.VOICE, channel.id, "auto_rename", False)
        execute(sql)
        await ctx.respond(f"auto rename for voice channel {channel.mention} disabled")
        return

    sql = updateById(DbTables.VOICE, channel.id, "auto_rename", True)
    execute(sql)
    await ctx.respond(f"auto rename for voice channel {channel.mention} enabled")


# intents = discord.Intents.default()
# intents.presences = True
# intents.members = True
# intents.message_content = True

bot.run(os.getenv("TOKEN"))