import re

from gdo.base.Method import Method
from gdo.discord.module_discord import module_discord


class invite(Method):
    @classmethod
    def gdo_trig(cls):
        return 'discord'

    def gdo_execute(self):
        code = module_discord.instance().get_config_val('invite_code') or ''
        if not re.fullmatch(r'[A-Za-z0-9-]{2,64}', code):
            return self.err('discord_invite_missing')
        return self.reply('discord_invite_link', (f'https://discord.gg/{code}',))
