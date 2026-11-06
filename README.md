# pygdo-discord
Discord connector for the PyGDO chatbot.

`$discord` (also `$discord.invite`) shows the configured `invite_code` as a
Discord invite link. Configure an invite intended for public sharing; the
method does not create or verify invites.

To watch a screen share, join the server and the voice channel containing a
LIVE broadcaster, select their name, and choose **Watch Stream**. Joining the
voice channel alone does not open the stream. See [Discord's Go Live help](https://support.discord.com/hc/en-us/articles/360040816151-Go-Live-and-Screen-Share).

Discord voice/stage channel joins, moves and departures map to PyGDO channel
join/left events. Mute changes do not. These events indicate voice membership,
not whether someone is watching a screen share. Discord does not expose normal
text-channel joins: writing a message remains a presence observation.

Guild member joins and departures emit `discord_member_joined` and
`discord_member_left` with the PyGDO user and guild ID; joins additionally
register the user on the PyGDO server. Departures do not imply a network-wide
quit, since the member may still be in another guild. Set `member_intent` only
after enabling the privileged Server Members Intent in Discord's developer
portal, then reconnect the connector. It defaults off so a missing portal grant
does not prevent the existing bot from connecting. No retrospective member
events or stream-viewer counts are inferred.
