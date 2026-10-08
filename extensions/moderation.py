from logging import getLogger

from discord import Embed, Interaction, Member
from discord.app_commands import command, default_permissions, describe
from discord.ext.commands import Bot, Cog

from database import Infraction, User, db

# this module is for moderation and its development will continue on /feature/modeartion branch
logger = getLogger("[Bot.Moderation]")


class Moderation(Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot: Bot = bot
        super().__init__()

    @command(name="warn", description="Use this command to warn a user")
    @default_permissions(manage_messages=True)
    @describe(member="The member you want to warn", reason="The reason for the warn")
    async def warn(self, interaction: Interaction, member: Member, reason: str):
        await interaction.response.defer(
            ephemeral=True
        )  # Defer cus we only have a 3 second response window

        async with db:
            # create/get user and add 1 to their infractions then save
            user, _ = await User.aget_or_create(user_id=member.id)
            print(user)
            user.infractions += 1
            await db.run(user.save)

            # create the infraction record then save
            infration: Infraction = await Infraction.acreate(
                user=user,
                moderator_id=interaction.user.id,
                reason=reason,
            )

            infractions: list[Infraction] = await db.run(
                lambda: Infraction.select().where(Infraction.type == "Warn").count()
            )

        infraction_embed = Embed(
            title=f"Warn # {infractions}",
            description=f"User: {member.mention}\nMod: {interaction.user.mention}\nReason: `{reason}`",
            color=0xFFFAA0,
        )
        await interaction.followup.send(
            content=f"{member.mention} Has been warned!", embed=infraction_embed
        )

    @command(name="cases", description="See all the cases a user has")
    @default_permissions(manage_messages=True)
    async def cases(self, interaction: Interaction, member: Member):
        await interaction.response.defer()
        async with db:
            cases: list[Infraction] = await db.run(
                lambda: (
                    Infraction.select()
                    .where(Infraction.user == User.get(user_id=member.id))
                    .order_by(Infraction.date.asc())
                )
            )
            await cases.aexecute()

            desc = "\n".join(
                f"{case.id}.) | `{case.type}` | {case.reason[:32]}" for case in cases
            )

        cases_embed = Embed(
            title=f"Cases for {member.global_name}",
            description=f"User: {member.mention}\n\n`case_id` | `case_type` | `reason`\n{desc}",
        )
        await interaction.followup.send(embed=cases_embed)


async def setup(bot: Bot):
    await bot.add_cog(Moderation(bot))
