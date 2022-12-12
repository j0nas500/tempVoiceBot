import datetime
from abc import ABC
from zoneinfo import ZoneInfo

import discord
from discord import bot, Spotify
from discord.ext import commands

from src.commands.voice.tools import update_voice_channel_name
from src.db.DbConnection import DbConnection
from src.db.DbTables import DbTables
from src.db.dbQueries import getTupelById, insertIntoVoiceChannels, updateById, insertIntoGuilds, deleteTupelById, \
    updateVoiceBitrate, getId


class EventsListener(commands.Bot, ABC):
    def __init__(self, db_connection: DbConnection):
        super().__init__(intents=discord.Intents.all())
        self.db_connection = db_connection

    async def on_ready(self):
        print(f"{self.user} is ready and online!")

    async def on_scheduled_event_create(self, event: discord.ScheduledEvent):
        if not event.guild.id == 257469328918577153:
            return
        embed = discord.Embed(
            title="Event erstellt",
            description=event.name,
            color=discord.Color.green(),
            timestamp=datetime.datetime.now(tz=ZoneInfo("Europe/Berlin"))
        )
        channel = event.guild.get_channel(1051714287355306015)
        if channel is None:
            return
        await channel.send(embeds=[embed])

    async def on_scheduled_event_delete(self, event: discord.ScheduledEvent):
        if not event.guild.id == 257469328918577153:
            return
        embed = discord.Embed(
            title="Event gelöscht",
            description=event.name,
            color=discord.Color.red(),
            timestamp=datetime.datetime.now(tz=ZoneInfo("Europe/Berlin"))
        )
        channel = event.guild.get_channel(1051714287355306015)
        if channel is None:
            return
        await channel.send(embeds=[embed])

    async def on_raw_scheduled_event_user_add(self, payload: discord.RawScheduledEventSubscription):
        if not payload.guild.id == 257469328918577153:
            return
        event: discord.ScheduledEvent = payload.guild.get_scheduled_event(payload.event_id)
        member: discord.Member = payload.guild.get_member(payload.user_id)
        if event is None or member is None:
            return
        embed = discord.Embed(
            title=f"{event.name}: User Add",
            description=member.mention,
            color=discord.Color.green(),
            timestamp=datetime.datetime.now(tz=ZoneInfo("Europe/Berlin"))
        )
        channel = event.guild.get_channel(1051714287355306015)
        if channel is None:
            return
        await channel.send(embeds=[embed])

    async def on_raw_scheduled_event_user_remove(self, payload: discord.RawScheduledEventSubscription):
        if not payload.guild.id == 257469328918577153:
            return
        event: discord.ScheduledEvent = payload.guild.get_scheduled_event(payload.event_id)
        member: discord.Member = payload.guild.get_member(payload.user_id)
        if event is None or member is None:
            return
        embed = discord.Embed(
            title=f"{event.name}: User Remove",
            description=member.mention,
            color=discord.Color.red(),
            timestamp=datetime.datetime.now(tz=ZoneInfo("Europe/Berlin"))
        )
        channel = event.guild.get_channel(1051714287355306015)
        if channel is None:
            return
        await channel.send(embeds=[embed])

    async def on_guild_join(self, guild: discord.Guild):
        print(f"{self.user} joined {self.guild.name}")
        sql = insertIntoGuilds(guild.id, int(guild.bitrate_limit))
        self.db_connection.execute(sql)

    async def on_guild_remove(self, guild: discord.Guild):
        print(f"{self.user} leaved {guild.name}")
        sql = deleteTupelById(DbTables.GUILDS, guild.id)
        self.db_connection.execute(sql)

    async def on_guild_update(self, guild_old: discord.Guild, guild_new: discord.Guild):
        if guild_old.bitrate_limit == guild_new.bitrate_limit:
            return
        print(f"{guild_new.name} Bitrate has changed to {guild_new.bitrate_limit}")
        sql = updateById(DbTables.GUILDS, guild_new.id, "bitrate_limit", guild_new.bitrate_limit)
        self.db_connection.execute(sql)
        if guild_old.bitrate_limit > guild_new.bitrate_limit:
            sql = updateVoiceBitrate(guild_new.id, guild_new.bitrate_limit)
            self.db_connection.execute(sql)

    async def on_guild_channel_delete(self, channel):
        sql = deleteTupelById(DbTables.VOICE, channel.id)
        result = self.db_connection.execute_rows(sql)
        if result > 0:
            print(f"Temporary Voice Channel {channel.id} removed")

    async def on_voice_state_update(self, member: discord.Member, voice_state_old: discord.VoiceState,
                                    voice_state_new: discord.VoiceState):
        channel_new: discord.VoiceChannel = voice_state_new.channel
        channel_old: discord.VoiceChannel = voice_state_old.channel

        if channel_new == channel_old:
            return

        if channel_new is not None:
            sql = getTupelById(DbTables.VOICE, channel_new.id, False)
            result = self.db_connection.execute_list(sql)
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
                self.db_connection.execute(sql)
                await member.move_to(channel=tmp_channel, reason="{member.name} joined temp Voice {channel_new.name}")
                overwrite = discord.PermissionOverwrite()
                overwrite.manage_channels = True
                overwrite.manage_permissions = True
                overwrite.move_members = True
                await tmp_channel.set_permissions(member, overwrite=overwrite)
                print(f"Temporary Voice Channel {tmp_channel.name} created by {member.name}")

            result = self.db_connection.execute_list(getTupelById(DbTables.VOICE, channel_new.id, True))
            if len(result) > 0:
                if int(result[0][6]) < 1:
                    return
                member: discord.Member = self.get_user(int(result[0][5]))
                await update_voice_channel_name(self.db_connection, member, channel_new)

        if channel_old is not None:
            result = self.db_connection.execute_list(getId(DbTables.VOICE, channel_old.id, True))
            if len(result) > 0:
                if len(channel_old.members) == 0:
                    await channel_old.delete(reason="No one in the temp voice channel")
                    return

                result = self.db_connection.execute_list(getTupelById(DbTables.VOICE, channel_old.id, True))
                if result[0][5] == member.id:
                    new_owner = channel_old.members[0]
                    sql = updateById(DbTables.VOICE, channel_old.id, "owner_id", new_owner.id)
                    overwrite = discord.PermissionOverwrite()
                    overwrite.manage_channels = True
                    overwrite.manage_permissions = True
                    overwrite.move_members = True
                    await channel_old.set_permissions(new_owner, overwrite=overwrite)
                    overwrite.manage_channels = None
                    overwrite.manage_permissions = None
                    overwrite.move_members = None
                    await channel_old.set_permissions(member, overwrite=overwrite)
                    print(f"{new_owner.name} is now the Owner of {channel_old.name} (old Owner: {member.name})")
                    self.db_connection.execute(sql)
                    if int(result[0][6]) < 1:
                        return
                    await update_voice_channel_name(self.db_connection, new_owner, channel_old)

                if int(result[0][6]) < 1:
                    return

                member: discord.Member = self.get_user(int(result[0][5]))
                await update_voice_channel_name(self.db_connection, member, channel_old)

    async def on_presence_update(self, member_old: discord.Member, member_new: discord.Member):
        if member_new.voice is None:
            return

        old_track_id = "same"
        new_track_id = "same"

        for activity in member_old.activities:
            if isinstance(activity, Spotify):
                old_track_id = activity.track_id

        for activity in member_new.activities:
            if isinstance(activity, Spotify):
                new_track_id = activity.track_id

        if old_track_id != new_track_id:
            return

        channel: discord.VoiceChannel = member_new.voice.channel

        result = self.db_connection.execute_list(getTupelById(DbTables.VOICE, channel.id, True))
        if len(result) < 1:
            return
        if int(result[0][6]) < 1:
            return

        member: discord.Member = self.get_user(int(result[0][5]))
        await update_voice_channel_name(self.db_connection, member, channel)
