import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

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
