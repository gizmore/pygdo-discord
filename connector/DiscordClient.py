from typing import TYPE_CHECKING
from pathlib import Path
from uuid import uuid4
from io import BytesIO

from PIL import Image

import discord

from gdo.base.Application import Application
from gdo.base.Message import Message
from gdo.base.Render import Mode
from gdo.core.GDO_Permission import GDO_Permission
from gdo.core.GDO_Server import GDO_Server
from gdo.core.GDO_UserPermission import GDO_UserPermission
from gdo.core.GDT_UserType import GDT_UserType
from gdo.core.GDO_File import GDO_File

if TYPE_CHECKING:
    from gdo.discord.connector.Discord import Discord

from gdo.base.Logger import Logger


class DiscordClient(discord.Client):

    IMAGE_MAX_BYTES = 10 * 1024 * 1024
    IMAGE_MAX_COUNT = 4
    IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/gif', 'image/webp'}

    @classmethod
    async def image_notices(cls, attachments):
        """Store bounded Discord image attachments and return local references."""
        notices = []
        images = [item for item in attachments if (item.content_type or '').split(';', 1)[0].lower() in cls.IMAGE_TYPES]
        for item in images[:cls.IMAGE_MAX_COUNT]:
            if not isinstance(item.size, int) or item.size < 1 or item.size > cls.IMAGE_MAX_BYTES:
                notices.append('[Discord image skipped: invalid or excessive size]')
                continue
            target = None
            try:
                data = await item.read()
                if not data or len(data) > cls.IMAGE_MAX_BYTES:
                    raise ValueError('invalid image size')
                with Image.open(BytesIO(data)) as image:
                    if image.format not in ('JPEG', 'PNG', 'GIF', 'WEBP'):
                        raise ValueError('invalid image format')
                    image.verify()
                directory = Path(Application.temp_path('discord/images'))
                directory.mkdir(parents=True, exist_ok=True)
                target = directory / uuid4().hex
                target.write_bytes(data)
                file = GDO_File.from_path(str(target), delete=True)
                file.set_val('file_name', Path(item.filename or 'image').name)
                file = file.insert()
                notices.append(f'[Discord image received: file://{file.get_path()} (file #{file.get_id()})]')
            except (OSError, ValueError, discord.DiscordException, Image.DecompressionBombError) as error:
                Logger.warning(f'Discord image download failed: {type(error).__name__}')
                notices.append('[Discord image unavailable]')
            finally:
                if target is not None:
                    target.unlink(missing_ok=True)
        if len(images) > cls.IMAGE_MAX_COUNT:
            notices.append('[Additional Discord images skipped]')
        return notices

    _connector: 'Discord'

    def connector(self, connector: 'Discord'):
        self._connector = connector
        return self

    def get_server(self) -> GDO_Server:
        return self._connector._server

    @staticmethod
    def refresh_displayname(user, displayname: str):
        """Persist a Discord-provided display name only when it changed."""
        if displayname and user.get_displayname() != displayname:
            user.save_val('user_displayname', displayname)

    async def on_ready(self):
        Logger.debug("Connected to Discord!")
        dog = await self.get_server().get_or_create_user(str(self.user.id), self.user.name)
        dog.save_val('user_type', GDT_UserType.CHAPPY)
        await GDO_UserPermission.grant(dog, GDO_Permission.ADMIN)
        await GDO_UserPermission.grant(dog, GDO_Permission.STAFF)
        self._connector._dog = dog

    async def _member_user(self, member):
        server = self.get_server()
        user = await server.get_or_create_user(str(member.id), member.display_name)
        self.refresh_displayname(user, member.display_name)
        user._network_user = member
        return user

    async def on_member_join(self, member):
        user = await self._member_user(member)
        await self.get_server().on_user_joined(user)
        await Application.EVENTS.publish('discord_member_joined', user, str(member.guild.id))

    async def on_member_remove(self, member):
        user = await self._member_user(member)
        # Discord guild membership is not the same as network-wide presence.
        # Keep it distinct: a user may remain in another guild or be uncached.
        await Application.EVENTS.publish('discord_member_left', user, str(member.guild.id))

    async def on_voice_state_update(self, member, before, after):
        old, new = before.channel, after.channel
        if getattr(old, 'id', None) == getattr(new, 'id', None):
            return
        server = self.get_server()
        user = await self._member_user(member)
        if old is not None:
            channel = server.get_or_create_channel(str(old.id), old.name)
            await channel.on_user_left(user)
        if new is not None:
            channel = server.get_or_create_channel(str(new.id), new.name)
            await server.on_user_joined(user, channel)
            await channel.on_user_joined(user)

    async def on_message(self, message):
        Application.tick()
        Logger.debug("Incoming message")
        serv = self.get_server()
        user = await serv.get_or_create_user(str(message.author.id), message.author.display_name)
        # Existing accounts may predate Discord's guild display name or have
        # since been renamed. Keep the visible local identity current without
        # writing on every message.
        self.refresh_displayname(user, message.author.display_name)
        user._network_user = message.author
        Logger.debug(f"{user.render_name()} >> {message.clean_content}")
        # Discord may deliver a message around reconnect before on_ready() has
        # populated the Dog account. A None marker is safe and avoids a race.
        if self._connector.gdo_get_dog_user() != user:
            chan = None
            if message.channel.type != discord.ChannelType.private:
                chan = serv.get_or_create_channel(str(message.channel.id), message.channel.name)
            # A message is a reliable presence observation even if Discord's
            # optional member-intent events are unavailable to this bot.
            await serv.on_user_joined(user, chan)
            if chan:
                await chan.on_user_joined(user)
            notices = await self.image_notices(message.attachments)
            text = '\n'.join(part for part in (message.clean_content, *notices) if part)
            if not text:
                return
            msg = Message(text, Mode.render_txt).env_user(user, True).env_server(serv).env_channel(chan)
            # Gateway messages identify the sending Discord account. Webhook
            # messages can impersonate display names and are not user logins.
            msg.platform_identity(message.author.id, trusted=message.webhook_id is None)
            await msg.execute()
