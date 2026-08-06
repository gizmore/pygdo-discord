import tomlkit

from gdo.base.GDO_Module import GDO_Module
from gdo.base.GDT import GDT
from gdo.core.Connector import Connector
from gdo.core.GDO_Server import GDO_Server
from gdo.core.GDT_Secret import GDT_Secret
from gdo.core.GDT_String import GDT_String
from gdo.discord.connector.Discord import Discord


class module_discord(GDO_Module):

    ##########
    # Config #
    ##########
    def gdo_module_config(self) -> list[GDT]:
        app_id = ""
        pubkey = ""
        secret = ""
        client = ""
        token = ""
        oauth = ""
        try:
            path = self.file_path('secret.toml')
            with open(path, 'r') as file:
                toml = tomlkit.load(file)
                app_id = toml.get('app_id', '')
                pubkey = toml.get('pubkey', '')
                secret = toml.get('secret', '')
                client = toml.get('client', '')
                token = toml.get('token', '')
                oauth = toml.get('oauth', '')
        except FileNotFoundError:
            pass
        return [
            GDT_Secret('discord_app_id').initial(app_id),
            GDT_Secret('discord_pubkey').initial(pubkey),
            GDT_Secret('discord_secret').initial(secret),
            GDT_Secret('discord_client').initial(client),
            GDT_Secret('discord_token').initial(token),
            GDT_String('discord_oauth').initial(oauth),
            GDT_String('invite_code').initial('ftWTRs3QQG'),
            GDT_String('bot_display_name').initial('Dog'),
            GDT_String('channel_display_name').initial('Shadowlamb'),
        ]

    def cfg_app_id(self) -> str:
        return self.get_config_val('discord_app_id')

    def cfg_pubkey(self) -> str:
        return self.get_config_val('discord_pubkey')

    def cfg_secret(self) -> str:
        return self.get_config_val('discord_secret')

    def cfg_client(self) -> str:
        return self.get_config_val('discord_client')

    def cfg_token(self) -> str:
        return self.get_config_val('discord_token')

    def cfg_oauth_url(self) -> str:
        return self.get_config_val('discord_oauth')

    ##########
    # Module #
    ##########
    def gdo_init(self):
        Connector.register(Discord)

    async def gdo_install(self):
        if not GDO_Server.get_by_connector('discord'):
            GDO_Server.blank({
                'serv_name': 'Discord',
                'serv_username': str(self.cfg_app_id()),
                'serv_connector': 'discord',
            }).insert()
