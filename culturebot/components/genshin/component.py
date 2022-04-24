import tanjun

group = tanjun.slash_command_group("genshin", "Genshin API")


user_group = group.with_command(tanjun.slash_command_group("user", "User settings."))


component = tanjun.Component(name="genshin").load_from_scope()
loader = component.make_loader()
