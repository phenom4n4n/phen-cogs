from .embed import EmbedUtils

__red_end_user_data_statement__ = "This cog stores End User Data when storing the author of an embed. If a user requests data-deletion, all their embeds will be removed from the bot."


def setup(bot):
    cog = EmbedUtils(bot)
    bot.add_cog(cog)
