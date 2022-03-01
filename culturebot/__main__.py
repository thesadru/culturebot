from . import client


if __name__ == "__main__":
    bot, _ = client.build_gateway_bot()
    bot.run()
