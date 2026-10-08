import logging
import os

from discord import Intents
from discord.ext.commands import Bot, Context, is_owner
from dotenv import load_dotenv

from database import Infraction, User, db

# any added extension gets its name here
extensions = ["moderation", "welcome"]
logger = logging.getLogger("[Bot]")


class RyanBaker(Bot):
    def __init__(self):
        super().__init__(command_prefix="?", intents=Intents.all())

    async def setup_hook(self) -> None:
        logger.info("Running setup hook")

        async with db:
            logger.info("setting up database")
            await db.acreate_tables([User, Infraction])

        for extension in extensions:
            await self.load_extension(f"extensions.{extension}")
        logger.info("Setup hook finished")


load_dotenv()

token: str = os.getenv("TOKEN")
if token is None:
    raise RuntimeError("Token is not set in .env")
bot = RyanBaker()


@bot.command()
@is_owner()
async def sync(ctx: Context):
    commands = await bot.tree.sync()
    await ctx.send(f"Synced {len(commands)} commands!")


bot.run(token)
