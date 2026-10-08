from discord import Embed, Member
from discord.ext.commands import Bot, Cog


class Welcome(Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        super().__init__()

    @Cog.listener(name="on_member_join")
    async def welcome(self, member: Member):
        join_channel = member.guild.get_channel(1557740013876281404)
        join_embed = Embed(
            title="Welcome to Ryan Baker's Server!",
            description=(
                "Be sure to check out <#1554479344494186518> and "
                "<#1554495257364926674>! Have questions? Check <#1556385643179941991> then post yours in <#1556385717741948938>"
            ),
            color=0x71FD8F,
        )
        join_embed.set_thumbnail(url=member.guild.icon)
        if member.avatar != None:
            join_embed.set_author(
                name=member.global_name,
                url=member.avatar.url,
                icon_url=member.avatar.url,
            )
        await join_channel.send(f"Welcome {member.mention}", embed=join_embed)


async def setup(bot: Bot):
    await bot.add_cog(Welcome(bot))
