from discord import Embed, Interaction, Member
from discord.ext.commands import Cog, Bot
from discord.app_commands import command, default_permissions, describe
from logging import getLogger

# this module is for moderation and its development will continue on /feature/modeartion branch
logger = getLogger("[Bot.Moderation]")


class Moderation(Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot: Bot = bot
        super().__init__()

    @command(name="warn", description="Use this command to warn a user")
    @default_permissions(
        manage_messages=True
    )  # require manage_messages permission to run this command
    @describe(user="The member you want to warn", reason="The reason for the warn")
    async def warn(self, interaction: Interaction, user: Member, reason: str):
        infraction_embed = Embed(
            title="Warn",
            description=f"User: {user.mention}\nMod: {interaction.user.mention}\nReason: `{reason}`",
            color=0xFFFAA0,
        )
        await interaction.response.send_message(
            content=f"{user.mention} Has been warned!", embed=infraction_embed
        )


async def setup(bot: Bot):
    await bot.add_cog(Moderation(bot))
