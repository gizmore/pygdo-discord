from typing import TYPE_CHECKING

import discord

from gdo.base.Application import Application
from gdo.base.Message import Message
from gdo.base.Render import Mode
from gdo.core.GDO_Permission import GDO_Permission
from gdo.core.GDO_Server import GDO_Server
from gdo.core.GDO_UserPermission import GDO_UserPermission
from gdo.core.GDT_UserType import GDT_UserType

if TYPE_CHECKING:
    from gdo.discord.connector.Discord import Discord

from gdo.base.Logger import Logger


class DiscordClient(discord.Client):

    _connector: 'Discord'

    def connector(self, connector: 'Discord'):
        self._connector = connector
        return self

    def get_server(self) -> GDO_Server:
        return self._connector._server

    async def on_ready(self):
        Logger.debug("Connected to Discord!")
        dog = self.get_server().get_or_create_user(str(self.user.id), self.user.name)
        dog.save_val('user_type', GDT_UserType.CHAPPY)
        GDO_UserPermission.grant(dog, GDO_Permission.ADMIN)
        GDO_UserPermission.grant(dog, GDO_Permission.STAFF)
        self._connector._dog = dog

    async def on_message(self, message):
        Application.tick()
        Logger.debug("Incoming message")
        serv = self.get_server()
        user = serv.get_or_create_user(str(message.author.id), message.author.display_name)
        user._discord_user = message.author
        if self._connector.gdo_get_dog_user() != user:
            chan = None
            if message.channel.type != discord.ChannelType.private:
                chan = serv.get_or_create_channel(str(message.channel.id), message.channel.name)
            Logger.debug(f"{user.render_name()} >> {message.clean_content}")
            msg = Message(message.clean_content, Mode.TXT).env_user(user).env_server(serv).env_channel(chan)
            await msg.execute()
