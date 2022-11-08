from src.db.DbTables import DbTables


def createTableVoiceChannels():
    return f"""CREATE TABLE IF NOT EXISTS {DbTables.VOICE.value}(
    id BIGINT UNSIGNED NOT NULL,
    guild_id BIGINT UNSIGNED NOT NULL,
    user_limit INT,
    bitrate INT,
    is_temp BOOLEAN NOT NULL,
    owner_id BIGINT,
    auto_rename BOOLEAN NOT NULL DEFAULT TRUE,
    is_ratelimited BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (id),
    FOREIGN KEY (guild_id) 
        REFERENCES guilds(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE)"""


def createTableRoles():
    return f"""CREATE TABLE IF NOT EXISTS {DbTables.ROLES.value}(
    id BIGINT UNSIGNED NOT NULL,
    guild_id BIGINT UNSIGNED NOT NULL,
    user_limit INT,
    bitrate INT,
    is_temp BOOLEAN NOT NULL,
    owner_id BIGINT,
    auto_rename BOOLEAN NOT NULL DEFAULT TRUE,
    is_ratelimited BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (id),
    FOREIGN KEY (guild_id) 
        REFERENCES guilds(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE)"""


def createTableGuilds():
    return f"""CREATE TABLE IF NOT EXISTS {DbTables.GUILDS.value}(
    id BIGINT UNSIGNED NOT NULL,
    bitrate_limit INT NOT NULL,
    PRIMARY KEY (id))
    """


def getId(table_name: DbTables, tupel_id, is_temp: bool = None):
    if is_temp is None:
        return f"SELECT id FROM {table_name.value} where id = {tupel_id}"
    return f"SELECT id FROM {table_name.value} where id = {tupel_id} AND is_temp = {is_temp}"


def getOwnerId(table_name: DbTables, tupel_id):
    return f"SELECT owner_id FROM {table_name.value} where id = {tupel_id} AND is_temp = TRUE"


def getIsRateLimited(table_name: DbTables, tupel_id):
    return f"SELECT is_ratelimited FROM {table_name.value} where id = {tupel_id}"


def getTupelById(table_name: DbTables, tupel_id, is_temp: bool = None):
    if is_temp is None:
        return f"SELECT * FROM {table_name.value} where id = {tupel_id}"
    return f"SELECT * FROM {table_name.value} where id = {tupel_id} AND is_temp = {is_temp}"


def insertIntoGuilds(guild_id, bitrate_limit: int):
    return f"INSERT INTO {DbTables.GUILDS.value} VALUES({guild_id}, {bitrate_limit})"


def updateById(table_name: DbTables, tupel_id, column_name: str, value):
    return f"UPDATE {table_name.value} SET {column_name} = {value} where id = {tupel_id}"


def updateVoiceBitrate(guild_id, new_bitrate):
    return f"UPDATE {DbTables.VOICE.value} SET bitrate = {new_bitrate} where guild_id = {guild_id} AND bitrate > {new_bitrate}"


def insertIntoVoiceChannels(voice_channel_id, guild_id, is_temp: bool, user_limit: int = "Null", bitrate: int = "Null",
                            owner_id="Null", auto_rename: bool = True, is_ratelimited: bool = False):
    return f"INSERT INTO {DbTables.VOICE.value} VALUES({voice_channel_id}, {guild_id}, {user_limit}, {bitrate}, {is_temp}, {owner_id}, {auto_rename}, {is_ratelimited})"


def deleteTupelById(table_name: DbTables, tupel_id, is_temp: bool = None):
    if is_temp is None:
        select = getId(table_name, tupel_id)
        return f"DELETE FROM {table_name.value} where id = ({select})"
    select = getId(table_name, tupel_id, is_temp)
    return f"DELETE FROM {table_name.value} where id = ({select})"
