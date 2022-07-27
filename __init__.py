import nonebot
from configs.config import Config


Config.add_plugin_config(
    "ishop",
    "IMPORT_ISHOP_GOODS",
    True,
    help_="私人商店",
    default_value=True
)

nonebot.load_plugins("extensive_plugin/zhenxun_plugin_personalshop")
