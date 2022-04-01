import dataclasses
import inspect
import re
import typing
import unicodedata

import hikari
import tanchi

__all__ = ["INFOS"]

T = typing.TypeVar("T", bound=typing.Any)


@dataclasses.dataclass
class Info:
    callback: typing.Callable[[typing.Any], hikari.Embed]

    @property
    def name(self) -> str:
        return self.callback.__name__.split("info")[0]

    @property
    def description(self) -> str:
        return inspect.getdoc(self.callback) or ""

    @property
    def type(self) -> type:
        sig = tanchi.types.signature(self.callback, eval_str=True)
        return list(sig.parameters.values())[0].annotation

    def __repr__(self) -> str:
        return f"Info(name={self.name!r}, type={self.type.__qualname__})"


INFOS: typing.List[Info] = []


def register_info(callback: typing.Callable[[T], hikari.Embed]) -> typing.Callable[[T], hikari.Embed]:
    INFOS.append(Info(callback))

    return callback


def dtimestamp(time: hikari.SearchableSnowflakeish, format: str = "f") -> str:
    if isinstance(time, int):
        time = hikari.Snowflake(time).created_at

    return f"<t:{int(time.timestamp())}:{format}>"


@register_info
def userinfo(user: hikari.User):
    embed = (
        hikari.Embed(color=user.accent_color)
        .set_author(name=f"User: {user.username}", icon=user.display_avatar_url)
        .set_thumbnail(user.display_avatar_url)
        .add_field(
            "Bot Information" if user.is_bot else "User Information",
            f"Name: {user.username}#{user.discriminator}\n"
            f"ID: `{user.id}`\n"
            f"Created: {dtimestamp(user.id)}\n"
            f"Mention: {user.mention}\n",
        )
    )
    if user.flags:
        flag_names = [(flag.name or "?").replace("_", " ").title() for flag in user.flags]
        embed.add_field("Flags", "\n".join(flag_names)),

    if isinstance(user, hikari.Member):
        timedout_until = user.communication_disabled_until()  # why is this so loooong

        embed.add_field(
            "Member Information",
            f"Joined: {dtimestamp(user.joined_at)}\n"
            f"Roles: {', '.join(f'<@&{i}>' for i in user.role_ids if i != user.guild_id)}\n"
            + (f"Nickname: {user.nickname}\n" if user.nickname else "")
            + (f"Boosting Since: {dtimestamp(user.premium_since)}\n" if user.premium_since else "")
            + (f"Timed-Out Until: {dtimestamp(timedout_until)}\n" if timedout_until else "")
            + (f"Muted: {user.is_mute} | Deafened: {user.is_deaf}" if user.is_mute or user.is_deaf else ""),
        )

    return embed


@register_info
def channelinfo(channel: hikari.GuildChannel):
    t = hikari.ChannelType(channel.type).name.split("_")[-1].title()
    embed = (
        hikari.Embed()
        .set_author(name=f"{t} Channel: {channel.name}")
        .add_field(
            "Channel Information",
            f"Name: {channel.name}\n"
            f"ID: `{channel.id}`\n"
            f"Created: {dtimestamp(channel.id)}\n"
            f"Mention: {channel.mention}\n"
            f"Type: {t} Channel (`{int(channel.type)}`)\n"
            f"NSFW: {'yes' if channel.is_nsfw else 'no'}\n"
            f"Category: {f'<#{channel.parent_id}>' if channel.parent_id else 'None'}",
        )
    )

    if isinstance(channel, (hikari.GuildTextChannel, hikari.GuildNewsChannel)):
        embed.add_field(
            "Text Channel Information",
            f"Topic: {channel.topic}\n"
            + (
                f"Slowmode: {channel.rate_limit_per_user.seconds}\n"
                if isinstance(channel, hikari.GuildTextChannel) and channel.rate_limit_per_user
                else ""
            )
            + (
                f"Last Message: {dtimestamp(channel.last_message_id)} (`{channel.last_message_id}`)\n"
                if channel.last_message_id
                else ""
            ),
        )

    if isinstance(channel, (hikari.GuildVoiceChannel, hikari.GuildStageChannel)):
        embed.add_field(
            "Voice Channel Information",
            f"Bitrate: {channel.bitrate}\n"
            f"Region: {channel.region or 'Automatic'}\n"
            f"User Limit: {channel.user_limit or 'None'}\n",
        )

    return embed


@register_info
def emojiinfo(emoji: hikari.CustomEmoji):
    embed = (
        hikari.Embed()
        .set_author(name=f"Emoji: {emoji.name}")
        .set_thumbnail(emoji.url)
        .add_field(
            "Emoji Information",
            f"Name: {emoji.name}\n"
            f"ID: `{emoji.id}`\n"
            f"Animated: {'yes' if emoji.is_animated else 'no'}\n"
            f"Mention: {emoji.mention}\n",
        )
    )

    if isinstance(emoji, hikari.KnownCustomEmoji):
        embed.add_field(
            "Known Emoji Information",
            f"Guild ID: `{emoji.guild_id}`\n"
            f"Creator: {emoji.user.mention if emoji.user else 'unknown'}\n"
            f"Managed: {'yes' if emoji.is_managed else 'no'}\n"
            f"Available: {'yes' if emoji.is_available else 'no'}\n"
            f"Roles: {', '.join(f'<@&{i}>' for i in emoji.role_ids) if emoji.role_ids else '@everyone'}\n",
        )

    return embed


@register_info
def inviteinfo(invite: hikari.Invite):
    if invite.guild:
        embed = (
            hikari.Embed(description=invite.guild.description)
            .set_author(
                name=f"Server invite: {invite.guild.name}",
                icon=invite.guild.icon_url,
                url=f"https://discord.gg/{invite.code}",
            )
            .set_thumbnail(invite.guild.icon_url)
            .set_image(invite.guild.splash_url or invite.guild.banner_url)
            .add_field(
                "Server information",
                f"Name: {invite.guild.name}\n"
                f"ID: `{invite.guild.id}`\n"
                f"Created: {dtimestamp(invite.guild.id, 'D')}\n"
                f"Members: {invite.approximate_member_count} ({invite.approximate_active_member_count} online)",
                inline=True,
            )
        )
        if invite.channel:
            embed.add_field(
                "Channel information",
                f"Name: {invite.channel.name}\n"
                f"ID: `{invite.channel.id}`\n"
                f"Created: {dtimestamp(invite.channel.id, 'D')}\n"
                f"Mention: <#{invite.channel.id}>",
                inline=True,
            )

    elif invite.channel:
        embed = (
            hikari.Embed()
            .set_author(name=f"Group DM invite: {invite.channel.name}")
            .add_field(
                "Group DM information",
                f"Name: {invite.channel.name if invite.channel.name else f'<#{invite.channel.id}>'}\n"
                f"ID: `{invite.channel.id}`\n"
                f"Created: {dtimestamp(invite.channel.id, 'D')}\n"
                f"Members: {invite.approximate_member_count} ({invite.approximate_active_member_count} online)",
                inline=True,
            )
        )
    else:
        embed = hikari.Embed().set_author(name="Discord invite")

    embed.add_field(
        "Basic Information",
        f"Code: {invite.code}\n"
        f"Expires: {(dtimestamp(invite.expires_at) if invite.expires_at else 'Never')}\n"
        + (f"Target Type: {['', 'Stream', 'Activity'][int(invite.target_type)]}\n" if invite.target_type else "")
        + (f"Target User: {invite.target_user.mention} `{invite.target_user.id}`\n" if invite.target_user else ""),
    )

    if invite.inviter:
        embed.add_field(
            "Invite creator",
            f"Name: {invite.inviter.username}#{invite.inviter.discriminator}\n"
            f"ID: `{invite.inviter.id}`\n"
            f"Created: {dtimestamp(invite.inviter.id, 'D')}\n"
            f"Mention: {invite.inviter.mention}",
            inline=True,
        )

    if isinstance(invite, hikari.InviteWithMetadata):
        embed.add_field(
            "Metadata",
            f"Uses: {invite.uses}\n"
            f"Max uses: {invite.max_uses}\n"
            f"Created: {dtimestamp(invite.created_at)}\n"
            f"Temporary: {invite.is_temporary}\n",
            inline=True,
        )

    if invite.target_application:
        if invite.target_application.icon_url:
            embed.set_thumbnail(invite.target_application.icon_url)

        embed.add_field(
            "Target Activity",
            f"Name: {invite.target_application.name}\n"
            f"ID: `{invite.target_application.id}`\n"
            f"Description: {invite.target_application.description}\n"
            f"Public Key: `{invite.target_application.public_key.hex()}`",
        )

    return embed


@register_info
def serverinfo(guild: hikari.PartialGuild):
    embed = hikari.Embed()
    embed.set_author(name=f"Guild: {guild.name}", icon=guild.icon_url)
    embed.set_thumbnail(guild.icon_url)

    embed.add_field(
        "Server Information",
        f"Name: {guild.name}\n" f"ID: `{guild.id}`\n" f"Created: {dtimestamp(guild.id)}\n",
        inline=True,
    )

    if not isinstance(guild, (hikari.Guild, hikari.GuildPreview)):
        return embed

    embed.description = guild.description

    if isinstance(guild, (hikari.RESTGuild, hikari.GuildPreview)):
        embed.add_field(
            "Member Information",
            f"Members: {guild.approximate_member_count} ({guild.approximate_active_member_count} online)\n",
        )
    elif isinstance(guild, hikari.GatewayGuild):
        embed.add_field(
            "Member Information",
            f"Members: {guild.member_count}\n" + (f"Large: {guild.is_large}\n" if guild.is_large else ""),
        )

    if isinstance(guild, hikari.Guild):
        embed.add_field(
            "Hidden Information",
            f"Owner: <@{guild.owner_id}> `{guild.owner_id}`\n"
            f"AFK timeout: {guild.afk_timeout}\n"
            f"Locale: {guild.preferred_locale}\n"
            + (f"Has widget: yes\n" if guild.is_widget_enabled else "")
            + (f"NSFW Level: {hikari.GuildNSFWLevel(guild.nsfw_level).name}\n" if guild.nsfw_level else "")
            + (f"MFA enabled: yes\n" if guild.mfa_level else "")
            + (f"Vanity Invite: `discord.gg/{guild.vanity_url_code}`\n" if guild.vanity_url_code else "")
            + (f"Boosters: {guild.premium_subscription_count}\n" if guild.premium_subscription_count else "")
            + (f"Boost level: {int(guild.premium_tier)}\n" if guild.premium_tier else ""),
        )
    else:
        tier = (
            0
            + ("THREE_DAY_THREAD_ARCHIVE" in guild.features)
            + ("SEVEN_DAY_THREAD_ARCHIVE" in guild.features)
            + ("PRIVATE_THREADS" in guild.features)
        )
        embed.add_field("Hidden Information", f"Boost level: {tier}")

    if guild.features:
        special_feature_names = ", ".join(
            "`" + feature.replace("_", " ").title() + "`"
            for feature in (hikari.GuildFeature.COMMUNITY, hikari.GuildFeature.PARTNERED, hikari.GuildFeature.VERIFIED)
            if feature in guild.features
        )
        feature_names = "\n".join(feature for feature in sorted(guild.features))

        embed.add_field(
            "Features",
            special_feature_names + f"\n```\n{feature_names}\n```\n",
        )

    return embed


@register_info
def roleinfo(role: hikari.Role):
    embed = (
        hikari.Embed()
        .set_author(name=f"Role: {role.name}")
        .add_field(
            "Role Information",
            f"Name: {role.name}\n"
            f"ID: `{role.id}`\n"
            f"Created: {dtimestamp(role.id)}\n"
            f"Mention: {role.mention}\n"
            f"Position: {role.position}\n"
            f"Color: {role.color}\n"
            f"Mentionable: {'yes' if role.is_mentionable else 'no'}\n"
            f"Hoisted: {'yes' if role.is_hoisted else 'no'}\n"
            f"Permissions: [`{role.permissions.value}`](https://discordapi.com/permissions.html#{role.permissions.value})\n",
        )
    )

    return embed


@register_info
def messageinfo(message: hikari.Message):
    embed = (
        hikari.Embed()
        .set_author(name=f"Message", url=message.make_link(message.guild_id), icon=message.author.display_avatar_url)
        .add_field(
            "Message Information",
            f"ID: `{message.id}`\n"
            f"Created: {dtimestamp(message.timestamp)}\n"
            f"Type: {hikari.MessageType(message.type).name.replace('_', ' ').title()}\n"
            f"Channel: <#{message.channel_id}> (`{message.channel_id}`)\n"
            + (f"Nonce: `{message.nonce}`\n" if message.nonce and message.nonce != str(message.id) else "")
            + (f"Edited: {dtimestamp(message.edited_timestamp)}\n" if message.edited_timestamp else "")
            + (f"Pinned: yes\n" if message.is_pinned else "")
            + (f"Webhook: `{message.webhook_id}`\n" if message.webhook_id else ""),
        )
        .add_field(
            "Author Information",
            f"Name: {message.author.username}#{message.author.discriminator}\n"
            f"ID: `{message.author.id}`\n"
            f"Created: {dtimestamp(message.author.id)}\n"
            f"Mention: {message.author.mention}\n",
        )
    )
    if message.flags:
        flag_names = [(flag.name or "?").replace("_", " ").title() for flag in message.flags]
        embed.add_field("Flags", "\n".join(flag_names))

    if message.referenced_message:
        embed.add_field(
            "Referenced Message",
            f"ID: `{message.referenced_message.id}`\n"
            f"Created: {dtimestamp(message.referenced_message.timestamp)}\n"
            f"Author: {message.referenced_message.author.mention} (`{message.referenced_message.author.id}`)"
            f"Link: {message.referenced_message.make_link(message.referenced_message.guild_id)}",
        )

    if message.activity:
        embed.add_field(
            "Activity Information",
            f"Type: {hikari.MessageActivityType(message.activity.type).name.replace('_', ' ').title()}\n"
            f"Party ID: `{message.activity.party_id}`",
        )

    if message.application:
        embed.add_field(
            "Application Information",
            f"ID: `{message.application.id}`\n"
            f"Created: {dtimestamp(message.application.id)}\n"
            f"Name: {message.application.name}\n"
            + (f"Description: {message.application.description}" if message.application.description else ""),
        )
        embed.set_image(message.application.cover_image_url or message.application.icon_url)

    elif message.application_id:
        embed.add_field(
            "Application Information",
            f"ID: `{message.application_id}`\n"
            f"Created: {dtimestamp(message.application_id)}\n"
            f"Mention: <@{message.application_id}>\n",
        )

    if message.interaction:
        embed.add_field(
            "Interaction Information",
            f"ID: `{message.interaction.id}`\n"
            f"Created: {dtimestamp(message.interaction.id)}\n"
            f"Type: {hikari.InteractionType(message.interaction.type).name.replace('_', ' ').title()}\n"
            f"Name: {message.interaction.name}\n"
            f"User: {message.interaction.user.mention} (`{message.interaction.user.id}`)\n",
        )

    return embed


@register_info
def snowflakeinfo(snowflake: hikari.Snowflake):
    embed = (
        hikari.Embed()
        .set_author(
            name=f"Snowflake: {snowflake}",
            icon=hikari.UnicodeEmoji("❄️"),
            url=f"https://snowsta.mp/?s={snowflake}",
        )
        .add_field("Created At", f"{dtimestamp(snowflake)}")
        .add_field("Internal Worker ID", str(snowflake.internal_worker_id), inline=True)
        .add_field("Internal Process ID", str(snowflake.internal_process_id), inline=True)
        .add_field("Increment", str(snowflake.increment), inline=True)
    )

    return embed


@register_info
def colorinfo(color: hikari.Color):
    k = 1 - max(color.rgb_float)
    c, m, y = ((1 - x - k) / (1 - k) for x in color.rgb_float)
    k *= 100

    # TODO: Actually show the color?
    embed = (
        hikari.Embed(color=color)
        .set_author(name=f"Color {color.hex_code}")
        .add_field("RGB", f"Red: {color.rgb[0]}, Green: {color.rgb[1]}, Blue: {color.rgb[2]}")
        .add_field("CMYK", f"Cyan: {c:.0f}%, Magenta: {m:.0f}%, Yellow: {y:.0f}%, Black: {k:.0f}%")
        .add_field("Is Web-Safe?", "yes" if color.is_web_safe else "no")
    )

    return embed


def get_ucode(chars: str) -> str:
    codes = ""
    for char in chars:
        digit = f"{ord(char):x}"
        if len(digit) <= 4:
            codes += f"\\u{digit:>04}"
        else:
            codes += f"\\U{digit:>08}"

    return codes


@register_info
def characterinfo(string: str):
    string = re.sub(
        r"\\[uU]([a-fA-F0-9]{4,8})",
        lambda match: chr(int(match[1], 16)),
        string,
    )

    char_list = []
    for char in string:
        url = f"https://www.compart.com/en/unicode/U+{ord(char):x}"
        name = f"[{unicodedata.name(char, '')}]({url})"
        info = f"`{get_ucode(char).ljust(10)}` {name} - {char}"
        char_list.append(info)

    embed = (
        hikari.Embed(description="\n".join(char_list))
        .set_author(name="Character Info")
        .add_field(name="Full Raw Text", value=f"`{get_ucode(string)}`", inline=False)
        .add_field(
            name="Normalized",
            value="\n".join(
                f"{k}: `{get_ucode(norm := unicodedata.normalize(k, string))}` ({norm})"
                for k in ("NFC", "NFKC", "NFD", "NFKD")
            ),
        )
    )

    return embed
