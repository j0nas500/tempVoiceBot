import asyncio
from collections import Counter

import discord
from pyrate_limiter import RequestRate, Duration, Limiter, BucketFullException

from src.db.DbConnection import DbConnection
from src.db.DbTables import DbTables
from src.db.dbQueries import getIsRateLimited, updateById

rate = RequestRate(2, Duration.MINUTE * 10)
limiter = Limiter(rate)


async def waiting_rename_channel(db_connection: DbConnection, owner: discord.Member, channel: discord.VoiceChannel, seconds):
    sql = getIsRateLimited(DbTables.VOICE, channel.id)
    result = db_connection.execute_list(sql)
    if result[0][0] == 1:
        return
    sql = updateById(DbTables.VOICE, channel.id, "is_ratelimited", "TRUE")
    db_connection.execute(sql)
    print(f"Try again in {seconds} seconds")
    await asyncio.sleep(seconds)
    sql = updateById(DbTables.VOICE, channel.id, "is_ratelimited", "FALSE")
    db_connection.execute(sql)
    #print("FINISHED SLEEEPING")
    await update_voice_channel_name(owner, channel)


async def get_new_channel_name(owner: discord.Member, channel: discord.VoiceChannel):
    activities: list = []
    all_member = channel.members
    if len(all_member) < 1:
        return None

    for x in all_member:
        for y in x.activities:
            if y.type is discord.ActivityType.playing:
                # print(y.name)
                activities.append(y.name)
                break

    if len(activities) < 1:
        if channel.name == owner.name:
            return
        #print(f"{channel.name} new name will be {owner.name} [0]")
        return owner.name

    counts = dict(Counter(activities))
    highest_value_key = max(counts, key=counts.get)
    highest_value = counts.get(highest_value_key)

    if len(all_member) * 0.5 < highest_value:
        if channel.name == highest_value_key:
            return
        #print(f"{channel.name} new name will be {highest_value_key} [1]")
        return highest_value_key

    if channel.name == owner.name:
        return
    #print(f"{channel.name} new name will be {owner.name} [2]")
    return owner.name


async def update_voice_channel_name(db_connection: DbConnection, owner: discord.Member, channel: discord.VoiceChannel):
    new_name = await get_new_channel_name(owner, channel)
    if new_name is None:
        return

    try:
        limiter.try_acquire(channel.id)
        print(f"{channel.name} has been renamed to {new_name}")
        await channel.edit(name=new_name)
    except BucketFullException as err:
        print(f"{channel.name} can't be renamed to {new_name} cause Rate Limit")
        await waiting_rename_channel(owner, channel, 210)