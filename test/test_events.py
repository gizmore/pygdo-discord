import unittest
import io
import tempfile
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from PIL import Image

from gdo.discord.connector.DiscordClient import DiscordClient


class DiscordEventsTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.server = MagicMock()
        self.user = MagicMock()
        self.user.get_displayname.return_value = 'Alice'
        self.server.get_or_create_user = AsyncMock(return_value=self.user)
        self.server.on_user_joined = AsyncMock()
        self.old, self.new = MagicMock(), MagicMock()
        self.old.on_user_left = AsyncMock()
        self.new.on_user_joined = AsyncMock()
        self.server.get_or_create_channel.side_effect = lambda ident, name: self.old if ident == '1' else self.new
        self.client = object.__new__(DiscordClient)
        self.client._connector = MagicMock()
        self.client._connector._server = self.server
        self.member = SimpleNamespace(id=7, display_name='Alice', guild=SimpleNamespace(id=42))

    async def test_image_attachment_is_stored_and_referenced_locally(self):
        buffer = io.BytesIO()
        Image.new('RGB', (2, 2), 'red').save(buffer, format='PNG')
        data = buffer.getvalue()
        item = SimpleNamespace(content_type='image/png', size=len(data), filename='../photo.png', read=AsyncMock(return_value=data))
        file = MagicMock()
        file.insert.return_value = file
        file.get_path.return_value = '/private/123'
        file.get_id.return_value = '123'
        with tempfile.TemporaryDirectory() as directory, \
                patch('gdo.discord.connector.DiscordClient.Application.temp_path', return_value=directory), \
                patch('gdo.discord.connector.DiscordClient.GDO_File.from_path', return_value=file):
            notices = await self.client.image_notices([item])
        self.assertEqual(['[Discord image received: file:///private/123 (file #123)]'], notices)
        file.set_val.assert_called_once_with('file_name', 'photo.png')

    async def test_rejects_oversized_and_invalid_images(self):
        large = SimpleNamespace(content_type='image/png', size=DiscordClient.IMAGE_MAX_BYTES + 1, read=AsyncMock())
        invalid = SimpleNamespace(content_type='image/png', size=4, filename='bad.png', read=AsyncMock(return_value=b'nope'))
        with patch('gdo.discord.connector.DiscordClient.Logger.warning'):
            notices = await self.client.image_notices([large, invalid])
        large.read.assert_not_awaited()
        self.assertEqual(['[Discord image skipped: invalid or excessive size]', '[Discord image unavailable]'], notices)

    async def test_voice_move_and_mute(self):
        old = SimpleNamespace(id=1, name='old')
        new = SimpleNamespace(id=2, name='new')
        await self.client.on_voice_state_update(self.member, SimpleNamespace(channel=old), SimpleNamespace(channel=new))
        self.old.on_user_left.assert_awaited_once_with(self.user)
        self.server.on_user_joined.assert_awaited_once_with(self.user, self.new)
        self.new.on_user_joined.assert_awaited_once_with(self.user)
        self.server.reset_mock()
        await self.client.on_voice_state_update(self.member, SimpleNamespace(channel=new), SimpleNamespace(channel=new))
        self.server.get_or_create_user.assert_not_called()

    async def test_member_join_and_leave_are_guild_scoped(self):
        with patch('gdo.discord.connector.DiscordClient.Application.EVENTS', create=True) as events:
            events.publish = AsyncMock()
            await self.client.on_member_join(self.member)
            await self.client.on_member_remove(self.member)
            self.server.on_user_joined.assert_awaited_once_with(self.user)
            self.server.on_user_quit.assert_not_called()
            self.assertEqual(events.publish.await_args_list[0].args, ('discord_member_joined', self.user, '42'))
            self.assertEqual(events.publish.await_args_list[1].args, ('discord_member_left', self.user, '42'))

    async def test_only_normal_gateway_messages_trust_discord_identity(self):
        import discord
        for webhook_id, expected in ((None, True), (123, False)):
            with self.subTest(webhook_id=webhook_id):
                raw = SimpleNamespace(author=SimpleNamespace(id=7, display_name='Alice'),
                                      channel=SimpleNamespace(type=discord.ChannelType.private),
                                      webhook_id=webhook_id, attachments=[], clean_content='hello')
                message = MagicMock()
                message.env_user.return_value = message
                message.env_server.return_value = message
                message.env_channel.return_value = message
                message.execute = AsyncMock()
                self.client._connector.gdo_get_dog_user.return_value = None
                with patch('gdo.discord.connector.DiscordClient.Message', return_value=message), \
                        patch('gdo.discord.connector.DiscordClient.Application.tick'), \
                        patch('gdo.discord.connector.DiscordClient.Logger.debug'):
                    await self.client.on_message(raw)
                self.assertEqual(expected, message._platform_authenticated)
                message.execute.assert_awaited_once()
