from discord.ext.commands import Cog, Bot
from logging import getLogger

logger = getLogger("[Bot.Moderation]")


class Moderation(Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot: Bot = bot
        super().__init__()


async def setup(bot: Bot):
    await bot.add_cog(Moderation(bot))
