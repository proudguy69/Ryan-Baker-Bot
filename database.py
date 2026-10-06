# this file will contain sqlite peewee classes for things like moderation and levels
# pyright: reportOptionalMemberAccess=false, reportOptionalIterable=false, reportAssignmentType=false

from datetime import datetime

from peewee import IntegerField
from playhouse.pwasyncio import (
    AsyncSqliteDatabase,
    DateTimeField,
    ForeignKeyField,
    TextField,
)

db = AsyncSqliteDatabase("database.db", pragmas={"journal_mode": "wal"})


class User(db.Model):
    id = IntegerField(primary_key=True)
    user_id = IntegerField(unique=True)  # discord user_id
    infrations = IntegerField(default=0)
    messages = IntegerField(default=0)  # total number of messages sent
    xp = IntegerField(default=0)
    level = IntegerField(default=1)


class Infraction(db.Model):
    id = IntegerField(primary_key=True)
    user = ForeignKeyField(User, lazy_load=False, backref="infractions")
    moderator_id = IntegerField()
    type = TextField(default="Warn")
    reason = TextField(default="None Provided")
    date = DateTimeField(default=datetime.now)


async def main():
    # just a sample how how'd we create data
    async with db:
        await db.acreate_tables([User])

        # create
        user = await db.run(User.create, user_id=1)

        # get``
        user: User = await db.run(User.get, user_id=1)

        # edit

        user.infrations += 1
        await db.run(user.save)
