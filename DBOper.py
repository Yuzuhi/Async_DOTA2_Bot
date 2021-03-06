#!/usr/bin/python
# -*- coding: UTF-8 -*-
import os
import aiosqlite


class _Updater:

    def __init__(self, short_steamID=None, long_steamID=None):
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        self.db_path = os.path.join(BASE_DIR, 'playerInfo.db')
        self.short_steamID = short_steamID
        self.long_steamID = long_steamID


class Dota2StatusUpdater(_Updater):
    def __init__(self, short_steamID):
        super().__init__(short_steamID)

    async def update_DOTA2_match_ID(self, last_DOTA2_match_ID):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                f"UPDATE playerInfo SET last_DOTA2_match_ID='{last_DOTA2_match_ID}' WHERE short_steamID={self.short_steamID}"
            )
            await db.commit()

    async def insert_info(self, long_steamID, nickname, last_DOTA2_match_ID):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO playerInfo (short_steamID, long_steamID, nickname, last_DOTA2_match_ID) VALUES ({}, {}, '{}', '{}')".format(
                    self.short_steamID, long_steamID, nickname, last_DOTA2_match_ID))
            await db.commit()

    async def is_player_stored(self):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(f"SELECT * FROM playerInfo WHERE short_steamID=={self.short_steamID}") as cursor:
                async for row in cursor:
                    if len(list(row)) != 0:
                        return True
                return False


class SteamStatusUpdater(Dota2StatusUpdater):
    def __init__(self, short_steamID=None, long_steamID=None):
        super().__init__(short_steamID=None)
        self.long_steamID = long_steamID

    async def get_playing_game(self):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                    f"SELECT gamename, last_update FROM playerInfo WHERE long_steamID='{self.long_steamID}'") as cursor:
                row = await cursor.fetchone()
                return (row[0], row[1]) if all(row) else (None, 0)

    async def update_playing_game(self, game_name, timestamp):
        async with aiosqlite.connect(self.db_path) as db:
            sql = f"UPDATE playerInfo SET gamename='{game_name}', last_update='{timestamp}' WHERE long_steamID='{self.long_steamID}'"
            await db.execute(sql)
            await db.commit()

    async def get_nickname_by_long_steamID(self):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                    f"SELECT nickname FROM playerInfo WHERE long_steamID='{self.long_steamID}'"
            ) as cursor:
                row = await cursor.fetchone()
                return row[0]
