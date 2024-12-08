from typing import Any,TYPE_CHECKING

from gdo.base.Application import Application
from gdo.base.Message import Message
from gdo.base.Render import Mode
from gdo.core.GDO_Permission import GDO_Permission
from gdo.core.GDO_UserPermission import GDO_UserPermission

if TYPE_CHECKING:
    from gdo.discord.connector.Discord import Discord

import discord

from gdo.base.Logger import Logger


class DiscordClient(discord.Client):

    _connector: 'Discord'

    def connector(self, connector: 'Discord'):
        self._connector = connector
        return self
    
    async def on_ready(self):
        dog = self._connector._server.get_or_create_user(str(self.user.id), self.user.name)
        GDO_UserPermission.grant(dog, GDO_Permission.ADMIN)
        GDO_UserPermission.grant(dog, GDO_Permission.STAFF)
        self._connector._dog = dog

    async def on_message(self, message):
        Application.tick()
        serv = self._connector._server
        user = serv.get_or_create_user(str(message.author.id), message.author.display_name)
        chan = None
        if message.channel:
            chan = serv.get_or_create_channel(str(message.channel.id), message.channel.name)
        msg = Message(message.clean_content, Mode.TXT).env_user(user).env_server(serv).env_channel(chan)
        await msg.execute()


    def on_error(self, event_method: str, /, *args: Any, **kwargs: Any) -> None:
        Logger.error(event_method)
