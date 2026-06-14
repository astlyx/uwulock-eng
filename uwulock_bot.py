import os
import re
import json
import random

import discord
from discord.ext import commands

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ---------------- CONFIG ----------------
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
PREFIX = "!"
DATA_FILE = "uwulock_data.json"
WEBHOOK_NAME = "UwULock"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)


@bot.check
async def owner_only(ctx: commands.Context) -> bool:
    """Only the user with OWNER_ID can use bot commands."""
    return ctx.author.id == OWNER_ID


# ---------------- DATA (LOCKED USERS + STATS) ----------------
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}

    if "locks" not in data and "stats" not in data:
        # Legacy format: {guild_id: [user_id, ...]} — migrate it
        data = {"locks": data, "stats": {}}
    else:
        data.setdefault("locks", {})
        data.setdefault("stats", {})

    return data


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


locked_data = load_data()
# locked_data["locks"] -> {"guild_id": [user_id, ...]}
# locked_data["stats"] -> {"guild_id": {"user_id": uwu_count}}


def is_locked(guild_id: int, user_id: int) -> bool:
    return user_id in locked_data["locks"].get(str(guild_id), [])


def lock_user(guild_id: int, user_id: int):
    key = str(guild_id)
    locked_data["locks"].setdefault(key, [])
    if user_id not in locked_data["locks"][key]:
        locked_data["locks"][key].append(user_id)
        save_data(locked_data)


def unlock_user(guild_id: int, user_id: int):
    key = str(guild_id)
    if user_id in locked_data["locks"].get(key, []):
        locked_data["locks"][key].remove(user_id)
        save_data(locked_data)


def lock_users_bulk(guild_id: int, user_ids) -> int:
    """Lock multiple users at once. Returns how many were newly added."""
    key = str(guild_id)
    locked_data["locks"].setdefault(key, [])
    added = 0
    for uid in user_ids:
        if uid not in locked_data["locks"][key]:
            locked_data["locks"][key].append(uid)
            added += 1
    if added:
        save_data(locked_data)
    return added


def unlock_all(guild_id: int) -> int:
    """Remove all locks in a guild. Returns how many were removed."""
    key = str(guild_id)
    removed = len(locked_data["locks"].get(key, []))
    if removed:
        locked_data["locks"][key] = []
        save_data(locked_data)
    return removed


def increment_stat(guild_id: int, user_id: int):
    gkey, ukey = str(guild_id), str(user_id)
    locked_data["stats"].setdefault(gkey, {})
    locked_data["stats"][gkey][ukey] = locked_data["stats"][gkey].get(ukey, 0) + 1
    save_data(locked_data)


def get_stats(guild_id: int, limit: int = 10):
    gkey = str(guild_id)
    stats = locked_data["stats"].get(gkey, {})
    return sorted(stats.items(), key=lambda item: item[1], reverse=True)[:limit]


# ---------------- PRESENCE ----------------
STATUS_MAP = {
    "online": discord.Status.online,
    "idle": discord.Status.idle,
    "invisible": discord.Status.invisible,
    "dnd": discord.Status.dnd,
}

# Default status on startup (change if you prefer)
current_status = discord.Status.online


def total_locked_count() -> int:
    return sum(len(v) for v in locked_data["locks"].values())


async def update_presence():
    total = total_locked_count()
    if total == 0:
        text = "nobody uwulocked... yet 😏"
    elif total == 1:
        text = "1 person uwulocked 💕"
    else:
        text = f"{total} people uwulocked 💕"
    activity = discord.Activity(type=discord.ActivityType.watching, name=text)
    await bot.change_presence(status=current_status, activity=activity)


# ---------------- UWUIFY ----------------
FACES = [
    "uwu", "owo", "OwO", "UwU", ">w<", ":3", "nya~", "rawr x3", "(´｡• ᵕ •｡`)",
    "*blushes*", "*nuzzles*", "*purrs*", "*giggles*", "*hides face*",
    "*wags tail*", "*paws at you*", "*looks away shyly*", "*twirls hair*",
    "*sweats nervously*", "*covers face with hands*", "*bounces excitedly*",
]

EMOJIS = ["🥺", "💕", "✨", "🌸", "💖", "😳", "🐾", "💗", "✧"]

# These are protected from uwuification: code blocks, links, Discord
# mention/emoji/timestamp syntax. Otherwise links break and custom emojis corrupt.
PROTECTED_PATTERN = re.compile(
    r"```.*?```"                  # ```code block```
    r"|`[^`\n]*`"                 # `inline code`
    r"|https?://\S+"              # http(s) link
    r"|www\.\S+"                  # www link
    r"|<a?:\w+:\d+>"              # <:custom_emoji:12345>
    r"|<@!?\d+>"                  # <@user>
    r"|<@&\d+>"                   # <@&role>
    r"|<#\d+>"                    # <#channel>
    r"|<t:\d+(?::[tTdDfFR])?>",   # <t:timestamp>
    re.DOTALL,
)

# Word substitutions: keys must be lowercase
WORD_SUBSTITUTIONS = {
    "love": "wuv",
    "cute": "kawaii",
    "friend": "fwend",
    "friends": "fwends",
    "small": "smol",
    "this": "dis",
    "that": "dat",
    "the": "da",
    "hello": "hewwo",
    "world": "wowld",
    "what": "wat",
    "stupid": "baka",
    "please": "pwease",
    "because": "bcuz",
    "with": "wif",
    "good": "gud",
    "dog": "doggo",
    "cat": "kitty",
    "big": "beeg",
    "yes": "yus",
    "no": "nyo",
    "not": "nawt",
    "you": "chu",
    "your": "ur",
    "are": "awre",
    "have": "hav",
    "brother": "bwother",
    "sister": "sistew",
    "sorry": "sowwy",
    "thanks": "thankies",
    "thank": "fank",
    "okay": "owkay",
    "ok": "owk",
    "why": "wai",
    "really": "weawwy",
    "very": "vewy",
    "everyone": "evewyone",
    "everything": "evewything",
    "right": "wight",
    "wrong": "wwong",
    "never": "nevew",
    "always": "awways",
}

_WORD_SUB_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(w) for w in WORD_SUBSTITUTIONS) + r")\b",
    re.IGNORECASE,
)


def substitute_words(text: str) -> str:
    def repl(match):
        word = match.group(0)
        replacement = WORD_SUBSTITUTIONS[word.lower()]
        if word.isupper():
            return replacement.upper()
        if word[0].isupper():
            return replacement.capitalize()
        return replacement

    return _WORD_SUB_PATTERN.sub(repl, text)


def uwuify(text: str) -> str:
    if not text:
        return text

    # Protect links, code blocks, mentions, and custom emojis from modification
    protected = []

    def protect(match):
        protected.append(match.group(0))
        return f"§{len(protected) - 1}§"

    text = PROTECTED_PATTERN.sub(protect, text)

    # Word substitutions: love->wuv, cute->kawaii, friend->fwend etc.
    text = substitute_words(text)

    # l/r -> w (preserving case)
    def lr_to_w(match):
        ch = match.group(0)
        return "W" if ch in "LR" else "w"

    text = re.sub(r"[lrLR]", lr_to_w, text)

    # "na, ne, ni, no, nu" -> "nya, nye, nyi, nyo, nyu"
    def nasal(match):
        g = match.group(0)
        return g[0] + "y" + g[1:]

    text = re.sub(r"[nN][aeiouAEIOU]", nasal, text)

    # Random stuttering: "making" -> "m-m-making"
    words = text.split(" ")
    new_words = []
    for word in words:
        if word and word[0].isalpha() and random.random() < 0.35:
            n = random.randint(1, 3)
            stutter = "-".join([word[0]] * n)
            word = f"{stutter}-{word}"
        new_words.append(word)

    # Insert a random face expression
    if new_words and random.random() < 0.6:
        pos = random.randint(0, len(new_words))
        new_words.insert(pos, f"({random.choice(FACES)})")

    # Sprinkle in random emoji(s)
    if new_words and random.random() < 0.6:
        for _ in range(random.randint(1, 2)):
            pos = random.randint(0, len(new_words))
            new_words.insert(pos, random.choice(EMOJIS))

    text = " ".join(new_words)

    # Append a face at the end
    if random.random() < 0.7:
        text += " " + random.choice(FACES)

    # Restore protected sections (links, code, mentions, emojis)
    def restore(match):
        idx = int(match.group(1))
        if 0 <= idx < len(protected):
            return protected[idx]
        return match.group(0)

    text = re.sub(r"§(\d+)§", restore, text)

    return text[:2000]  # Discord message length limit


# ---------------- WEBHOOK MIMIC ----------------
async def get_or_create_webhook(channel: discord.TextChannel) -> discord.Webhook:
    webhooks = await channel.webhooks()
    for wh in webhooks:
        if wh.name == WEBHOOK_NAME and wh.user == bot.user:
            return wh
    return await channel.create_webhook(name=WEBHOOK_NAME)


async def mimic_message(message: discord.Message):
    increment_stat(message.guild.id, message.author.id)

    content = message.content
    uwu_text = uwuify(content) if content else None

    files = []
    for attachment in message.attachments:
        try:
            files.append(await attachment.to_file())
        except Exception:
            pass

    channel = message.channel
    thread = None
    if isinstance(channel, discord.Thread):
        thread = channel
        channel = channel.parent

    if channel is None:
        return

    try:
        webhook = await get_or_create_webhook(channel)
    except discord.Forbidden:
        return

    try:
        await message.delete()
    except (discord.Forbidden, discord.NotFound):
        pass

    send_kwargs = dict(
        content=uwu_text,
        username=message.author.display_name,
        avatar_url=message.author.display_avatar.url,
        files=files,
    )
    if thread is not None:
        send_kwargs["thread"] = thread

    try:
        await webhook.send(**send_kwargs)
    except discord.HTTPException:
        pass


# ---------------- EVENTS ----------------
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}, ready to uwuify!")
    await update_presence()


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    if message.guild and is_locked(message.guild.id, message.author.id):
        if not message.content.startswith(PREFIX):
            await mimic_message(message)
            return

    await bot.process_commands(message)


@bot.event
async def on_message_edit(before: discord.Message, after: discord.Message):
    if after.author.bot:
        return

    # Discord sometimes fires this event when adding a link preview (embed);
    # ignore if the actual text hasn't changed.
    if before.content == after.content:
        return

    if after.guild and is_locked(after.guild.id, after.author.id):
        if not after.content.startswith(PREFIX):
            await mimic_message(after)


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        # Only the owner can use commands — stay silent for everyone else
        return
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have permission to use this command! 😤")
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("Couldn't find that member.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(
            f"Missing argument. Usage: `{PREFIX}{ctx.command} {ctx.command.signature}`"
        )
    else:
        raise error


# ---------------- COMMANDS ----------------
@bot.command(name="uwulock")
async def uwulock_cmd(ctx, member: discord.Member):
    if member.id == bot.user.id:
        await ctx.send("You can't uwulock me! 😤")
        return
    if member.bot:
        await ctx.send("You can't uwulock bots.")
        return
    lock_user(ctx.guild.id, member.id)
    await update_presence()
    await ctx.send(f"🔒 {member.mention} is now **uwulocked**! UwU")


@bot.command(name="uwuunlock", aliases=["unlock"])
async def uwuunlock_cmd(ctx, member: discord.Member):
    unlock_user(ctx.guild.id, member.id)
    await update_presence()
    await ctx.send(f"🔓 {member.mention} is free. (for now)")


@bot.command(name="uwulockall")
async def uwulockall_cmd(ctx):
    targets = [
        m.id for m in ctx.guild.members
        if not m.bot and m.id != OWNER_ID and m.id != bot.user.id
    ]
    added = lock_users_bulk(ctx.guild.id, targets)
    await update_presence()
    await ctx.send(
        f"🔒 **{added}** people have been uwulocked! Everyone speaks UwU now~ "
        f"*wags tail*"
    )


@bot.command(name="uwuunlockall")
async def uwuunlockall_cmd(ctx):
    removed = unlock_all(ctx.guild.id)
    await update_presence()
    if removed == 0:
        await ctx.send("Nobody was locked to begin with.")
        return
    await ctx.send(f"🔓 **{removed}** people have been freed. For now!")


@bot.command(name="uwulist")
async def uwulist_cmd(ctx):
    ids = locked_data["locks"].get(str(ctx.guild.id), [])
    if not ids:
        await ctx.send("Nobody is currently uwulocked.")
        return
    mentions = ", ".join(f"<@{uid}>" for uid in ids)
    await ctx.send(f"Currently locked: {mentions}")


@bot.command(name="uwuify")
async def uwuify_cmd(ctx, *, text: str):
    await ctx.send(uwuify(text))


@bot.command(name="uwustats")
async def uwustats_cmd(ctx):
    stats = get_stats(ctx.guild.id)
    if not stats:
        await ctx.send("Nobody has been uwulocked yet... for now. 😏")
        return

    medals = ["🥇", "🥈", "🥉"]
    lines = []
    for i, (user_id, count) in enumerate(stats):
        prefix = medals[i] if i < len(medals) else f"`{i + 1}.`"
        lines.append(f"{prefix} <@{user_id}> — uwulocked **{count}** time(s)")

    embed = discord.Embed(
        title="UwU Leaderboard 🏆",
        description="\n".join(lines),
        color=discord.Color.pink(),
    )
    await ctx.send(embed=embed)


@bot.command(name="uwuhelp")
async def uwuhelp_cmd(ctx):
    embed = discord.Embed(
        title="UwULock Bot Commands",
        description=(
            f"`{PREFIX}uwulock @user` - Uwulock a user\n"
            f"`{PREFIX}uwuunlock @user` (`{PREFIX}unlock @user`) - Release a user\n"
            f"`{PREFIX}uwulockall` - Uwulock everyone in the server (except owner)\n"
            f"`{PREFIX}uwuunlockall` - Release everyone\n"
            f"`{PREFIX}uwulist` - List currently locked users\n"
            f"`{PREFIX}uwuify <text>` - Uwuify a message (for testing)\n"
            f"`{PREFIX}uwustats` - Show the UwU leaderboard\n"
            f"`{PREFIX}uwustatus <status>` - Change bot status "
            f"(online/idle/invisible/dnd)\n"
            f"`{PREFIX}shutdown` - Shut the bot down completely\n\n"
            "⚠️ All commands are restricted to the bot owner only.\n"
            "💡 The bot's presence shows how many people are currently uwulocked."
        ),
        color=discord.Color.pink(),
    )
    await ctx.send(embed=embed)


@bot.command(name="shutdown")
async def shutdown_cmd(ctx):
    await ctx.send("Shutting down... see you! 👋")
    await bot.close()


@bot.command(name="uwustatus")
async def uwustatus_cmd(ctx, status: str):
    global current_status

    status_key = status.lower()
    if status_key not in STATUS_MAP:
        valid = ", ".join(sorted(STATUS_MAP.keys()))
        await ctx.send(f"Invalid status. Valid options: {valid}")
        return

    current_status = STATUS_MAP[status_key]
    await update_presence()
    await ctx.send(f"✅ Bot status set to **{status}**.")


# ---------------- START ----------------
if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError(
            "DISCORD_BOT_TOKEN is not set! Add it to your .env file or environment variables."
        )
    if OWNER_ID == 0:
        raise RuntimeError(
            "OWNER_ID is not set! Add your Discord user ID to your .env file."
        )
    bot.run(TOKEN)
