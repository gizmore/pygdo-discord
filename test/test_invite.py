import unittest
from unittest.mock import MagicMock, patch

from gdo.discord.method.invite import invite
from gdo.base.Application import Application
from gdo.base.Render import Mode


class InviteTest(unittest.TestCase):
    def setUp(self):
        Application.mode(Mode.render_cli)

    def test_configured_invite(self):
        method = invite()
        method.reply = MagicMock(return_value='ok')
        module = MagicMock()
        module.get_config_val.return_value = 'abc-123'
        with patch('gdo.discord.method.invite.module_discord.instance', return_value=module):
            self.assertEqual('ok', method.gdo_execute())
        self.assertEqual('discord', method.gdo_trig())
        method.reply.assert_called_once_with('discord_invite_link', ('https://discord.gg/abc-123',))

    def test_invalid_invite_is_not_published(self):
        method = invite()
        method.err = MagicMock(return_value='error')
        module = MagicMock()
        module.get_config_val.return_value = 'bad/code'
        with patch('gdo.discord.method.invite.module_discord.instance', return_value=module):
            self.assertEqual('error', method.gdo_execute())
