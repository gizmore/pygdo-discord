import asyncio

import discord

from gdo.base.Logger import Logger
from gdo.base.Message import Message
from gdo.core.Connector import Connector
from gdo.core.GDO_User import GDO_User
from gdo.discord.connector.DiscordClient import DiscordClient


class Discord(Connector):

    _client: DiscordClient
    _dog: GDO_User

    def gdo_connect(self):
        from gdo.discord.module_discord import module_discord
        Logger.debug("Connecting to discord.")
        intents = discord.Intents.default()
        intents.message_content = True
        intents.presences = True
        self._client = DiscordClient(intents=intents).connector(self)
        module = module_discord.instance()
        asyncio.create_task(self._client.start(module.cfg_token(), reconnect=True))
        self._connected = True
        return True

    def gdo_get_dog_user(self) -> GDO_User:
        return self._dog

    async def gdo_send_to_channel(self, message: Message):
        channel = message._env_channel
        text = message._result[:4096]
        Logger.debug(f"{channel.render_name()} << {text}")
        prefix = f'{message._env_user.render_name()}: ' if not message._thread_user else ''
        text = f"{prefix}{text}"
        await self._client.get_channel(int(channel.get_name())).send(text)

    async def gdo_send_to_user(self, message: Message):
        text = message._result[:4096]
        user = message._env_user
        Logger.debug(f"{user.render_name()} << {text}")
        await self._client.get_user(int(user.get_name())).send(text)