import json

from datetime import datetime

import aiohttp as aiohttp

from config import API_KEY, PLAYER_LIST, ENABLE_USE_STEAM_NICKNAME
from DBOper import *


async def gaming_status_watcher():
    """
    请求游戏状态
    :return:
    """
    timeout = aiohttp.ClientTimeout(total=330, connect=2, sock_connect=15, sock_read=10)
    async with aiohttp.ClientSession() as session:
        replays = []
        sids = ','.join(str(p[1] + 76561197960265728) for p in PLAYER_LIST)
        url = f'http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={API_KEY}&steamids={sids}'
        async with session.get(url=url, timeout=50) as result:
            # data = await result.read()
            print(result)
            
            j = await result.json(content_type=None)
            for p in j['response']['players']:
                sid = int(p['steamid'])
                cur_game = p.get('gameextrainfo', None)
                # 创建一个更新steam状态的实例对象
                steam_updater = SteamStatusUpdater(long_steamID=sid)
                pname = p[
                    'personaname'] if ENABLE_USE_STEAM_NICKNAME else await steam_updater.get_nickname_by_long_steamID()
                pre_game, last_update = await steam_updater.get_playing_game()
                pre_game = None if pre_game == 'None' else pre_game
                print(f"{pname}正在游玩{cur_game}")
                # 游戏状态更新
                if cur_game != pre_game:
                    print('更新游戏状态')
                    # status_changed = True
                    now = int(datetime.now().timestamp())
                    minutes = (now - last_update) // 60
                    if cur_game:
                        if pre_game:
                            replays.append(f'{pname}玩了{minutes}分钟{pre_game}后，玩起了{cur_game}')
                        else:
                            replays.append(f'{pname}启动了{cur_game}')
                    else:
                        replays.append(f'{pname}退出了{pre_game}，本次游戏时长{minutes}分钟')
                    await steam_updater.update_playing_game(cur_game, now)

        return '\n'.join(replays) if replays else None


