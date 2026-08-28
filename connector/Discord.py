import asyncio

import discord

from gdo.base.Logger import Logger
from gdo.base.Message import Message
from gdo.base.Render import Mode
from gdo.base.Util import Strings, module_config_value
from gdo.core.Connector import Connector
from gdo.core.GDO_User import GDO_User
from gdo.discord.connector.DiscordClient import DiscordClient


class Discord(Connector):

    MAX_MSG_LEN: int = 1980  # gizmore birth year seems appropriate

    _client: DiscordClient
    _client_task: asyncio.Task|None
    _dog: GDO_User|None

    def render_user_connect_help(self) -> str:
        return f'<a href="https://discord.gg/{module_config_value('discord', 'invite_code')}">{module_config_value('discord', 'channel_display_name')}</a> ({module_config_value('discord', 'bot_display_name')})'

    def get_render_mode(self) -> Mode:
        return Mode.render_markdown

    def gdo_needs_authentication(self) -> bool:
        return False

    def __init__(self):
        super().__init__()
        self._client = None
        self._client_task = None
        self._dog = None

    async def gdo_connect(self) -> bool:
        from gdo.discord.module_discord import module_discord
        Logger.debug("Connecting to discord.")
        intents = discord.Intents.default()
        intents.message_content = True
        intents.presences = True
        self._client = DiscordClient(intents=intents).connector(self)
        module = module_discord.instance()
        self._client_task = asyncio.create_task(self._client.start(module.cfg_token(), reconnect=True))
        self._connected = True
        return True

    async def gdo_disconnect(self, quit_message: str):
        """Close discord.py explicitly so its internal reconnect loop stops."""
        if self._client and not self._client.is_closed():
            await self._client.close()
        if self._client_task and not self._client_task.done():
            try:
                await asyncio.wait_for(self._client_task, timeout=5)
            except TimeoutError:
                self._client_task.cancel()
        self._client_task = None
        self._client = None

    def gdo_get_dog_user(self) -> GDO_User|None:
        return self._dog

    async def gdo_send_to_channel(self, message: Message):
        text = message._result
        channel = message._env_channel
        Logger.debug(f"{channel.render_name()} << {text}")
        prefix = f'{message._env_user.render_name()}: ' if not message._thread_user else ''
        text = f"{prefix}{text}"
        chan = self._client.get_channel(int(channel.get_name()))
        chunks = Strings.split_boundary(text, self.MAX_MSG_LEN)
        for chunk in chunks:
            await chan.send(chunk)

    async def gdo_send_to_user(self, message: Message, notice: bool=False):
        text = message._result
        user = message._env_user
        Logger.debug(f"{user.render_name()} << {text}")
        usr = user._network_user
        if usr is None:
            try:
                usr = await self._client.fetch_user(int(user.get_name()))
                user._network_user = usr
            except (ValueError, discord.HTTPException) as ex:
                Logger.error(f"Cannot resolve Discord DM user {user.get_name()}: {ex}")
                return
        try:
            for chunk in Strings.split_boundary(text, self.MAX_MSG_LEN):
                await usr.send(chunk)
        except discord.HTTPException as ex:
            Logger.error(f"Cannot send Discord DM to {user.get_name()}: {ex}")
