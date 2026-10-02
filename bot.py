from discord.ext.commands import Bot, Context
from discord import Intents
from dotenv import load_dotenv
import os
import logging

# any added extension gets its name here
extensions = ["moderation"]
logger = logging.getLogger("[Bot]")


class RyanBaker(Bot):
    def __init__(self):
        super().__init__(command_prefix="?", intents=Intents.all())

    async def setup_hook(self) -> None:
        logger.info("Running setup hook")
        for extension in extensions:
            await self.load_extension(f"extensions.{extension}")
        logger.info("Setup hook finished")


load_dotenv()

token: str = os.getenv("TOKEN")
if token is None:
    raise RuntimeError("Token is not set in .env")
bot = RyanBaker()

bot.run(token)
