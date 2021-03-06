#!/usr/bin/python
# -*- coding: UTF-8 -*-
import asyncio
import time
import json
import config
from DBOper import Dota2StatusUpdater
from player import PLAYER_LIST, player

from common import steam_id_convert_32_to_64, update_and_send_message_DOTA2, update_and_send_gaming_status
import DOTA2
import message_sender


async def init():
    # 读取配置文件
    player_list = config.PLAYER_LIST
    # 读取玩家信息
    for i in player_list:
        nickname = i[0]
        short_steamID = i[1]
        print("{}信息读取完毕, ID:{}".format(nickname, short_steamID))
        long_steamID = steam_id_convert_32_to_64(short_steamID)

        try:
            last_DOTA2_match_ID = await DOTA2.get_last_match_id_by_short_steamID(short_steamID)
        except DOTA2.DOTA2HTTPError:
            last_DOTA2_match_ID = "-1"
        # 创建一个数据库操作实例
        update_instance = Dota2StatusUpdater(short_steamID=short_steamID)
        # 如果数据库中没有这个人的信息, 则进行数据库插入
        if not await update_instance.is_player_stored():
            # 插入数据库
            await update_instance.insert_info(long_steamID, nickname, last_DOTA2_match_ID)
        # 如果有这个人的信息则更新其最新的比赛信息
        else:
            await update_instance.update_DOTA2_match_ID(last_DOTA2_match_ID)
        # 新建一个玩家对象, 放入玩家列表
        temp_player = player(short_steamID=short_steamID,
                             long_steamID=long_steamID,
                             nickname=nickname,
                             last_DOTA2_match_ID=last_DOTA2_match_ID)

        PLAYER_LIST.append(temp_player)


async def sleep_between_update(player_num: int):
    # dota每日请求限制100,000次
    # 每个人假设每次更新都需要请求两次
    # 所以请求间隔可以设置为 (24 * 60 * 60 / (100000 / (2 * player_num)))
    # 10个人的情况下, 会17秒更新一次信息
    # 但是其实每分钟更新一次即可保证及时
    if player_num >= 30:
        await asyncio.sleep((24 * 60 * 60) / (100000 / (2 * player_num)))
    else:
        await asyncio.sleep(60)


async def game_info_watcher():
    if config.ENABLE_STEAM_WATCHER:
        print("steam游戏监听初始化完成, 开始更新steam状态")
        while True:
            player_num = len(PLAYER_LIST)
            if player_num == 0:
                return
            await update_and_send_gaming_status()
            await sleep_between_update(player_num=player_num)


async def dota2_info_watcher():
    print("dota2监听初始化完成, 开始更新dota2状态")
    while True:
        player_num = len(PLAYER_LIST)
        if player_num == 0:
            return
        await update_and_send_message_DOTA2()
        await sleep_between_update(player_num=player_num)


# 监听群内聊天
async def message_listener():
    pass


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    # 初始化
    loop.run_until_complete(init())
    task_list = [
        game_info_watcher(),
        dota2_info_watcher(),
        message_listener()
    ]
    asyncio.run(asyncio.wait(task_list))


