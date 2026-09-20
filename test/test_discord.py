import unittest
from unittest.mock import MagicMock

from gdo.discord.connector.DiscordClient import DiscordClient


class DiscordDisplayNameTest(unittest.TestCase):

    def test_refreshes_only_a_changed_display_name(self):
        user = MagicMock()
        user.get_displayname.return_value = 'Old name'

        DiscordClient.refresh_displayname(user, 'New name')

        user.save_val.assert_called_once_with('user_displayname', 'New name')

    def test_keeps_matching_or_empty_display_names_write_free(self):
        user = MagicMock()
        user.get_displayname.return_value = 'Same name'

        DiscordClient.refresh_displayname(user, 'Same name')
        DiscordClient.refresh_displayname(user, '')

        user.save_val.assert_not_called()
