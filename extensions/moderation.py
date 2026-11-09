from logging import getLogger

from discord import Embed, Forbidden, HTTPException, Interaction, Member
from discord import User as DiscordUser
from discord.app_commands import (
    AppCommandError,
    Choice,
    MissingPermissions,
    Range,
    checks,
    choices,
    command,
    default_permissions,
    describe,
    guild_only,
)
from discord.ext.commands import Bot, Cog

from database import Infraction, User, db

# this module is for moderation and its development will continue on /feature/modeartion branch
logger = getLogger("[Bot.Moderation]")
SEARCH_LIMIT = 15  # most cases shown in one search, keeps the embed under Discord's size limit


class Moderation(Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot: Bot = bot
        super().__init__()

    @command(name="warn", description="Use this command to warn a user")
    @guild_only()
    @default_permissions(manage_messages=True)
    @describe(member="The member you want to warn", reason="The reason for the warn")
    async def warn(self, interaction: Interaction, member: Member, reason: str):
        await interaction.response.defer(
            ephemeral=True
        )  # Defer cus we only have a 3 second response window

        async with db:
            # create/get user and add 1 to their infractions then save
            # (the column is spelled "infrations"; "infractions" is the list of their cases)
            user, _ = await User.aget_or_create(user_id=member.id)
            user.infrations += 1
            await user.asave()

            # create the infraction record then save
            await Infraction.acreate(
                user=user,
                moderator_id=interaction.user.id,
                reason=reason,
            )

            # this user's warn count, not the whole server's
            warn_count: int = await db.run(
                Infraction.select()
                .where((Infraction.user == user) & (Infraction.type == "Warn"))
                .count
            )

        infraction_embed = Embed(
            title=f"Warn # {warn_count}",
            description=f"User: {member.mention}\nMod: {interaction.user.mention}\nReason: `{reason}`",
            color=0xFFFAA0,
        )
        await interaction.followup.send(
            content=f"{member.mention} Has been warned!", embed=infraction_embed
        )

    @command(name="cases", description="See all the cases a user has")
    @guild_only()
    @default_permissions(manage_messages=True)
    @describe(member="The user to look up (works for banned users too, paste their ID)")
    async def cases(self, interaction: Interaction, member: DiscordUser):
        await interaction.response.defer()
        async with db:
            cases = await db.list(
                Infraction.select()
                .join(User)
                .where(User.user_id == member.id)
                .order_by(Infraction.date.asc())
            )

        desc = "\n".join(
            f"{case.id}.) | `{case.type}` | {case.reason[:32]}" for case in cases
        ) or "No cases."

        cases_embed = Embed(
            title=f"Cases for {member.display_name}",
            description=f"User: {member.mention}\n\n`case_id` | `case_type` | `reason`\n{desc}"[:4000],
        )
        await interaction.followup.send(embed=cases_embed)

    @command(name="searchcases", description="Search cases by user, moderator, type, reason or case number")
    @guild_only()
    @default_permissions(manage_messages=True)
    @describe(
        case_id="Show one case by its number",
        user="Only cases for this user (works for banned users too)",
        moderator="Only cases made by this moderator",
        type="Only this type of case",
        reason="Only cases whose reason contains this text",
    )
    @choices(type=[Choice(name="Warn", value="Warn"), Choice(name="Ban", value="Ban")])
    async def searchcases(
        self,
        interaction: Interaction,
        case_id: int | None = None,
        user: DiscordUser | None = None,
        moderator: DiscordUser | None = None,
        type: Choice[str] | None = None,
        reason: str | None = None,
    ):
        await interaction.response.defer(ephemeral=True)

        query = Infraction.select(Infraction, User).join(User)
        filters = []
        if case_id is not None:
            query = query.where(Infraction.id == case_id)
            filters.append(f"case #{case_id}")
        if user is not None:
            query = query.where(User.user_id == user.id)
            filters.append(f"user {user.mention}")
        if moderator is not None:
            query = query.where(Infraction.moderator_id == moderator.id)
            filters.append(f"mod {moderator.mention}")
        if type is not None:
            query = query.where(Infraction.type == type.value)
            filters.append(f"type `{type.value}`")
        if reason:
            query = query.where(Infraction.reason.contains(reason))
            filters.append(f"reason contains `{reason}`")

        async with db:
            total: int = await db.run(query.count)
            cases = await db.list(query.order_by(Infraction.date.desc()).limit(SEARCH_LIMIT))

        if not cases:
            await interaction.followup.send("No cases match that search.", ephemeral=True)
            return

        lines = [
            f"**#{case.id}** `{case.type}` <@{case.user.user_id}> by <@{case.moderator_id}> "
            f"<t:{int(case.date.timestamp())}:d>\n{case.reason[:100]}"
            for case in cases
        ]
        shown = f"Showing the newest {len(cases)} of {total}" if total > len(cases) else f"{total} found"
        search_embed = Embed(
            title="Case search",
            description=(
                f"Filters: {', '.join(filters) or 'none (all cases)'}\n{shown}\n\n" + "\n\n".join(lines)
            )[:4000],
        )
        await interaction.followup.send(embed=search_embed, ephemeral=True)

    @command(name="ban", description="Ban a member from the server (admins only)")
    @guild_only()
    # default_permissions hides the command from non-admins; the check enforces it
    # even if a server setting re-enables the command for other roles
    @default_permissions(administrator=True)
    @checks.has_permissions(administrator=True)
    @describe(
        member="The member you want to ban",
        reason="The reason for the ban",
        delete_days="Delete their messages from the last N days (0-7)",
    )
    async def ban(
        self,
        interaction: Interaction,
        member: Member,
        reason: str = "None Provided",
        delete_days: Range[int, 0, 7] = 0,
    ):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        mod = interaction.user

        # Safety checks before touching anything
        problem = None
        if member.id == mod.id:
            problem = "You can't ban yourself."
        elif member.id == self.bot.user.id:
            problem = "I can't ban myself."
        elif member.id == guild.owner_id:
            problem = "You can't ban the server owner."
        elif mod.id != guild.owner_id and member.top_role >= mod.top_role:
            problem = f"{member.mention} has a role equal to or higher than yours."
        elif member.top_role >= guild.me.top_role:
            problem = f"{member.mention} has a role equal to or higher than mine, so I can't ban them."
        if problem:
            await interaction.followup.send(problem, ephemeral=True)
            return

        # Tell them why before banning (fails quietly if their DMs are closed)
        try:
            await member.send(f"You have been banned from **{guild.name}**.\nReason: `{reason}`")
        except (Forbidden, HTTPException):
            pass

        try:
            await member.ban(
                reason=f"{reason} (banned by {mod} / {mod.id})",
                delete_message_seconds=delete_days * 86400,
            )
        except Forbidden:
            await interaction.followup.send(
                "I don't have permission to ban that member. Give my role **Ban Members**.",
                ephemeral=True,
            )
            return

        async with db:
            user, _ = await User.aget_or_create(user_id=member.id)
            user.infrations += 1
            await user.asave()
            infraction: Infraction = await Infraction.acreate(
                user=user,
                moderator_id=mod.id,
                type="Ban",
                reason=reason,
            )

        logger.info(f"{mod} ({mod.id}) banned {member} ({member.id}): {reason}")
        ban_embed = Embed(
            title=f"Ban | Case #{infraction.id}",
            description=f"User: {member.mention} (`{member.id}`)\nMod: {mod.mention}\nReason: `{reason}`",
            color=0xFF6B6B,
        )
        await interaction.followup.send(
            content=f"{member} has been banned.", embed=ban_embed
        )

    async def cog_app_command_error(
        self, interaction: Interaction, error: AppCommandError
    ):
        if isinstance(error, MissingPermissions):
            msg = "Only admins can use this command."
        else:
            logger.exception("Moderation command failed", exc_info=error)
            msg = "Something went wrong running that command."
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)


async def setup(bot: Bot):
    await bot.add_cog(Moderation(bot))
