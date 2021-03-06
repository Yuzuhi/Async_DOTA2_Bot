#!/usr/bin/python
# -*- coding: UTF-8 -*-
import aiohttp

from DOTA2_dicts import *
from player import player
import random
import time
from typing import Dict
from config import API_KEY, ENABLE_URL, DEFAULT_NAME_ONLY, ENABLE_SEND_GOOD_MESSAGE_ONLY


# 异常处理
class DOTA2HTTPError(Exception):
    pass


# 根据slot判断队伍, 返回1为天辉, 2为夜魇
def get_team_by_slot(slot: int) -> int:
    if slot < 100:
        return 1
    else:
        return 2


async def get_last_match_id_by_short_steamID(short_steamID: int) -> int:
    # get match_id
    url = 'https://api.steampowered.com/IDOTA2Match_570/GetMatchHistory/v001/?key={}' \
          '&account_id={}&matches_requested=1'.format(API_KEY, short_steamID)
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url=url, timeout=50) as response:
                result = await response.json(content_type=None)
                if result["result"]['status'] == 401:
                    raise DOTA2HTTPError("Unauthorized request 401. Verify API key.")
                elif result["result"]['status'] == 503:
                    raise DOTA2HTTPError("The server is busy or you exceeded limits. Please wait 30s and try again.")
                elif result["result"]['status'] >= 400:
                    raise DOTA2HTTPError(
                        "Failed to retrieve data: %s. URL: %s" % (result['status_code'], url))
        except Exception as e:
            print(e)
            raise DOTA2HTTPError("Requests Error")

    try:
        match_id = result["result"]["matches"][0]["match_id"]
    except KeyError:
        raise DOTA2HTTPError("Response Error: Key Error")
    except IndexError:
        raise DOTA2HTTPError("Response Error: Index Error")
    return match_id


async def get_match_detail_info(match_id: int) -> Dict:
    # get match detail
    url = 'https://api.steampowered.com/IDOTA2Match_570/GetMatchDetails/V001/' \
          '?key={}&match_id={}'.format(API_KEY, match_id)
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url=url, timeout=50) as response:
                status_code = response.status
                response = await response.json(content_type=None)
                if status_code >= 400:
                    if status_code == 401:
                        raise DOTA2HTTPError("Unauthorized request 401. Verify API key.")
                    elif status_code == 503:
                        raise DOTA2HTTPError(
                            "The server is busy or you exceeded limits. Please wait 30s and try again.")
                    else:
                        raise DOTA2HTTPError("Failed to retrieve data: %s. URL: %s" % (response.status_code, url))
        except Exception:
            raise DOTA2HTTPError("Requests Error")
    try:
        match_info = response['result']
    except KeyError:
        raise DOTA2HTTPError("Response Error: Key Error")
    except IndexError:
        raise DOTA2HTTPError("Response Error: Index Error")

    return match_info


# 接收某局比赛的玩家列表, 生成比赛战报
# 参数为玩家对象列表和比赛ID
async def generate_match_message(match_id: int, player_list: [player]):
    try:
        match = await get_match_detail_info(match_id=match_id)
    except DOTA2HTTPError:
        return "DOTA2比赛战报生成失败"

    start_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(match['start_time']))
    duration = match['duration']

    # 比赛模式
    mode_id = match["game_mode"]
    mode = GAME_MODE.get(mode_id, '未知')

    lobby_id = match['lobby_type']
    lobby = LOBBY.get(lobby_id, '未知')

    player_num = len(player_list)
    nicknames = '，'.join([player_list[i].nickname for i in range(-player_num, -1)])
    if nicknames:
        nicknames += '和'
    nicknames += player_list[-1].nickname

    # 更新玩家对象的比赛信息
    for i in player_list:
        for j in match['players']:
            if i.short_steamID == j['account_id']:
                i.dota2_kill = j['kills']
                i.dota2_death = j['deaths']
                i.dota2_assist = j['assists']
                i.kda = ((1. * i.dota2_kill + i.dota2_assist) / i.dota2_death) \
                    if i.dota2_death != 0 else (1. * i.dota2_kill + i.dota2_assist)

                i.dota2_team = get_team_by_slot(j['player_slot'])
                i.hero = j['hero_id']
                i.last_hit = j['last_hits']
                i.damage = j['hero_damage']
                i.gpm = j['gold_per_min']
                i.xpm = j['xp_per_min']
                break

    team = player_list[0].dota2_team
    win = match['radiant_win'] == (team == 1)

    if mode_id in (15, 19):  # 各种活动模式仅简单通报
        return '{}玩了一把[{}/{}]，开始于{}，持续{}分{}秒，看起来好像是{}了。'.format(
            nicknames, mode, lobby, start_time, duration // 60, duration % 60, "赢" if win else "输"
        )
    # 队伍信息
    team_damage = 0
    team_kills = 0
    team_deaths = 0
    for i in match['players']:
        if get_team_by_slot(i['player_slot']) == team:
            team_damage += i['hero_damage']
            team_kills += i['kills']
            team_deaths += i['deaths']

    top_kda = 0
    for i in player_list:
        if i.kda > top_kda:
            top_kda = i.kda

    if (win and top_kda > 10) or (not win and top_kda > 6):
        postive = True
    elif (win and top_kda < 4) or (not win and top_kda < 1):
        postive = False
    else:
        if random.randint(0, 1) == 0:
            postive = True
        else:
            postive = False

    tosend = []

    if ENABLE_SEND_GOOD_MESSAGE_ONLY and (win and postive):
        tosend.append(random.choice(WIN_POSTIVE_PARTY).format(nicknames))
    elif win and not postive:
        tosend.append(random.choice(WIN_NEGATIVE_PARTY).format(nicknames))
    elif not win and postive:
        tosend.append(random.choice(LOSE_POSTIVE_PARTY).format(nicknames))
    elif win and postive:
        return
    else:
        tosend.append(random.choice(LOSE_NEGATIVE_PARTY).format(nicknames))

    tosend.append('开始时间: {}'.format(start_time))
    tosend.append('持续时间: {}分{}秒'.format(duration // 60, duration % 60))
    tosend.append('游戏模式: [{}/{}]'.format(mode, lobby))

    for i in player_list:
        nickname = i.nickname
        if i.hero in HEROES_LIST_CHINESE:
            if DEFAULT_NAME_ONLY:
                hero = HEROES_LIST_CHINESE[i.hero][0]
            else:
                hero = random.choice(HEROES_LIST_CHINESE[i.hero])
        else:
            hero = '不知道什么鬼'
        kda = i.kda
        last_hits = i.last_hit
        damage = i.damage
        kills, deaths, assists = i.dota2_kill, i.dota2_death, i.dota2_assist
        gpm, xpm = i.gpm, i.xpm

        damage_rate = 0 if team_damage == 0 else (100 * (float(damage) / team_damage))
        participation = 0 if team_kills == 0 else (100 * float(kills + assists) / team_kills)
        deaths_rate = 0 if team_deaths == 0 else (100 * float(deaths) / team_deaths)

        tosend.append(
            '{}使用{}, KDA: {:.2f}[{}/{}/{}], GPM/XPM: {}/{}, ' \
            '补刀数: {}, 总伤害: {}({:.2f}%), 参战率: {:.2f}%, 参葬率: {:.2f}%' \
                .format(nickname, hero, kda, kills, deaths, assists, gpm, xpm, last_hits,
                        damage, damage_rate, participation, deaths_rate)
        )

    if ENABLE_URL:
        tosend.append('战绩详情: https://zh.dotabuff.com/matches/{}'.format(match_id))

    return '\n'.join(tosend)
