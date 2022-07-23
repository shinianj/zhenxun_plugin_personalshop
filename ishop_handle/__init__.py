from .idata_source import create_shop_help, delete_goods, update_goods, register_goods, parse_goods_info
from nonebot.adapters.onebot.v11 import MessageEvent, Message,GROUP
from nonebot import on_command
from configs.path_config import IMAGE_PATH
from utils.message_builder import image
from nonebot.permission import SUPERUSER
from utils.utils import is_number, scheduler
from nonebot.params import CommandArg
from nonebot.plugin import export
from services.log import logger
import os

__zx_plugin_name__ = "私人商店"
__plugin_usage__ = """
usage：
    私人商店项目，小真寻做见证人
    指令：
        私人商店
""".strip()
__plugin_superuser_usage__ = """
usage：
    商品操作
    指令：
        #交易||#摆摊 name:[名称] num:[数量] price:[价格]
        #下架 name:[名称] num:[数量]
        #修改价格 name:[名称或序号] price:[价格]
        示例：#交易||#摆摊 name:真寻 num:1 price:999
        示例：#下架 name:真寻 num:1
        示例：#修改价格 name:真寻 price:1   修改名称为真寻的商品的价格为1
""".strip()
__plugin_des__ = "私人商店系统[货物流通+金币回收计划]"
__plugin_cmd__ = [
    "私人商店",
        "#交易||#摆摊 name:[名称] num:[数量] price:[价格]",
        "#下架 name:[名称] num:[数量]",
        "#修改价格 name:[名称或序号] price:[价格]",
]
__plugin_type__ = ('私人商店',)
__plugin_version__ = 0.0
__plugin_author__ = "十年"
__plugin_settings__ = {
    "level": 5,
    "default_status": True,
    "limit_superuser": False,
    "cmd": ["私人商店"],
}
__plugin_block_limit__ = {
    "limit_type": "group"
}

# 导出方法供其他插件使用
export = export()
export.register_goods = register_goods
export.delete_goods = delete_goods
export.update_goods = update_goods

shop_help = on_command("私人商店", priority=5, block=True)

shop_add_goods = on_command("#上架", priority=5, permission=GROUP, block=True)

shop_del_goods = on_command("#下架", priority=5, permission=GROUP, block=True)

shop_update_goods = on_command("#修改商品", priority=5, permission=GROUP, block=True)


@shop_help.handle()
async def _():
    await shop_help.send(image(b64=await create_shop_help()))


@shop_add_goods.handle()
async def _(event: MessageEvent, arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip()
    if msg:
        data = parse_goods_info(msg)
        if isinstance(data, str):
            await shop_add_goods.finish(data)
        if not data.get("name") or not data.get("price") or not data.get("num"):
            await shop_add_goods.finish("name:price:num 参数不可缺少！")
        if await register_goods(**data):
            await shop_add_goods.send(f"上架商品 {data['name']} 成功！\n"
                                      f"名称：{data['name']}\n"
                                      f"数量：{data['num']}\n"
                                      f"价格：{data['price']}金币\n")
            logger.info(f"USER {event.user_id} 上架商品 {msg} 成功")
        else:
            await shop_add_goods.send(f"上架商品 {msg} 失败了...", at_sender=True)
            logger.warning(f"USER {event.user_id} 上架商品 {msg} 失败")


@shop_del_goods.handle()
async def _(event: MessageEvent, arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip()
    if msg:
        name = ""
        if not is_number(msg):
            name = msg
        else:
            await shop_del_goods.finish("请输入一个商品名")
        goods_name,goods_num,code = await delete_goods(name)
        if code == 200:
            await shop_del_goods.send(f"下架商品 {goods_name} 共{goods_num}成功了...", at_sender=True)
            if os.path.exists(f"{IMAGE_PATH}/shop_help.png"):
                os.remove(f"{IMAGE_PATH}/shop_help.png")
            logger.info(f"USER {event.user_id} 下架商品 {goods_name}共{goods_num} 成功")
        else:
            await shop_del_goods.send(f"下架商品 {goods_name}共{goods_num} 失败了...", at_sender=True)
            logger.info(f"USER {event.user_id} 下架商品 {goods_name} 共{goods_num}失败")


@shop_update_goods.handle()
async def _(event: MessageEvent, arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip()
    if msg:
        data = parse_goods_info(msg)
        if isinstance(data, str):
            await shop_add_goods.finish(data)
        if not data.get("name"):
            await shop_add_goods.finish("name 参数不可缺少！")
        flag, name, text = await update_goods(**data)
        if flag:
            await shop_update_goods.send(f"修改商品 {name} 成功了...\n{text}", at_sender=True)
            logger.info(f"USER {event.user_id} 修改商品 {name} 数据 {text} 成功")
        else:
            await shop_update_goods.send(name, at_sender=True)
            logger.info(f"USER {event.user_id} 修改商品 {name} 数据 {text} 失败")


