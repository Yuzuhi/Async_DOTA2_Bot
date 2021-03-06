#!/usr/bin/python
# -*- coding: UTF-8 -*-
import json

import aiohttp
import config

url = config.MIRAI_URL
# 群号
target = config.QQ_GROUP_ID
# bot的QQ号
bot_qq = config.BOT_QQ
# mirai http的auth key
authKey = config.MIRAI_AUTH_KEY


async def send_message(message: str):
    # Authorize
    auth_key = {"authKey": authKey}
    async with aiohttp.ClientSession() as session:
        async with session.post(url + "/auth", data=json.dumps(auth_key)) as response:
            print('generating session')
            result = await response.json()
    if result.get('code') != 0:
        print("ERROR@auth")
        print(result.text)
        exit(1)

    # Verify
    session_key = result['session']
    data = {"sessionKey": session_key, "qq": bot_qq}
    async with aiohttp.ClientSession() as session:
        async with session.post(url + "/verify", data=json.dumps(data)) as response:
            print('verifying session')
            result = await response.json()

    if result.get('code') != 0:
        print("ERROR@verify")
        print(result.text)
        exit(2)
    data = {
        "sessionKey": session_key,
        "target": target,
        "messageChain": [
            {"type": "Plain", "text": message}
        ]
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url + "/sendGroupMessage", data=json.dumps(data)) as response:
            print('发送群消息')

    # release

    data = {
        "sessionKey": session_key,
        "qq": bot_qq
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url + "/release", data=json.dumps(data)) as response:
            print('释放session')
