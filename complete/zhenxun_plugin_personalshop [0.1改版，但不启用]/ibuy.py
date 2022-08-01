from nonebot import on_command
from services.log import logger
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message
from nonebot.params import CommandArg
from utils.utils import is_number,get_message_at
from models.bag_user import BagUser
from services.db_context import db
from nonebot.adapters.onebot.v11.permission import GROUP
from configs.config import NICKNAME
from ._personal_goodsinfo import func_text,PersonalGoods
from models.group_member_info import GroupInfoUser
from utils.message_builder import at


__zx_plugin_name__ = "私人商店 - 购买道具"
__plugin_usage__ = """
usage：
    购买道具
    指令：
        私人交易||逛该 [名称] ?[数量=1]+艾特[目标]
        示例：逛该 好感双倍加持卡Ⅰ 1 @堂主
        示例：私人交易 4 1 @十年(名称长度8字符及以上的商品使用代替id优化展示)
""".strip()
__plugin_des__ = "私人商店 - 购买道具"
__plugin_cmd__ = ["购买 [名称] ?[数量=1]"]
__plugin_type__ = ("商店",)
__plugin_version__ = 9.1
__plugin_author__ = "十年"
__plugin_settings__ = {
    "level": 5,
    "default_status": True,
    "limit_superuser": False,
    "cmd": ["商店", "购买道具"],
}
__plugin_cd_limit__ = {"cd": 3}


buy = on_command("私人交易", aliases={"逛该"}, priority=5, block=True, permission=GROUP)


@buy.handle()
async def _(event: GroupMessageEvent, arg: Message = CommandArg()):
    qq = get_message_at(event.json())[0]
    qq_name = await GroupInfoUser.get_group_member_nickname(qq,event.group_id)
    group = event.group_id
    buyer_name = await GroupInfoUser.get_group_member_nickname(event.user_id,event.group_id)
    goods_lst = await PersonalGoods.get_goods(qq,event.group_id)
    goods_name_list = []
    for i,p in enumerate(goods_lst.keys()):
        goods_name_list.append(p)
    msg = arg.extract_plain_text().strip().split()
    num = 1
    if len(msg) > 1:
        if is_number(msg[1]) and int(msg[1]) > 0:
            num = int(msg[1])
        else:
            await buy.finish("购买的数量要是数字且大于0！", at_sender=True)
    if is_number(msg[0]):
        msg = int(msg[0])
        if msg > len(goods_name_list) or msg < 1:
            await buy.finish("请输入正确的替代商品名id！", at_sender=True)
        goods_name_lst = await PersonalGoods.get_replace_goods(qq,group)
        na = str(msg)
        for i in range(len(goods_name_list)):
            name = goods_name_lst[na]['name']
            goods_price = goods_name_lst[na]['price']
            break
    else:
        if msg[0] in goods_name_list:
            name = str(msg[0])
            for i in range(len(goods_name_list)):
                if msg[0] == goods_name_list[i]:
                    goods_price = goods_lst[msg[0]]['price']
                    break
            else:
                await buy.finish("请输入正确的商品名称！或检查是否是该商店中拥有的商品！")
        else:
            await buy.finish("请输入正确的商品名称！", at_sender=True)
    async with db.transaction():
        need_money = int(goods_price) * num
        if (
            await BagUser.get_gold(event.user_id, event.group_id)
        ) < need_money :
            await buy.finish("您的金币好像不太够哦", at_sender=True)
        get_money = need_money * 0.95
        #goods_num = await PersonalGoods.decode_num(goods_lst[msg[0]])
        #tax = need_money - get_money
        if  not await PersonalGoods.change_goods_now(qq,group,name,num) :
            await buy.finish(f'该商品已经买完咯，叫商家补货或是到别家看看吧')
        else:
            #goods_price = goods_lst[(msg[0])]['price']
            await PersonalGoods.add_goods_now(qq,event.group_id,name,num,goods_price)
            i = bool(await BagUser.spend_gold(event.user_id, event.group_id, need_money))
            if not i  :
                await BagUser.add_gold(qq,event.group_id,int(get_money))
                await BagUser.add_property(event.user_id,event.group_id,name)
                await PersonalGoods.change_goods_now(qq,event.group_id,name,num)
                await buy.send(
                    f"花费 {need_money } 金币购买 {qq_name} 的 {name} ×{num} 成功！",
                    at_sender=True,
                )
                logger.info(
                    f"USER {event.user_id} GROUP {event.group_id} "
                    f"花费 {need_money} 金币购买 {qq_name} 的 {name} ×{num} 成功！"
                )
                await buy.send(
                    at(qq) + f"  {buyer_name} 花费 {need_money } 金币购买您的 {name} ×{num} 成功！\n 已将{get_money}放入您的钱包，{NICKNAME}将收取5%的管理费哦",
                )
                logger.info(
                    f"USER {qq} GROUP {event.group_id} "
                    f"{qq_name}  {buyer_name} 花费 {need_money } 金币购买 {qq_name} 的 {name} ×{num} 成功！\n 已将{get_money}放入他的钱包，{NICKNAME}将收取5%的管理费哦"
                )
            else:
                await buy.send(f'{str(i)}')
                await buy.send(f"{name} 购买失败！", at_sender=True)
                logger.info(
                    f"USER {event.user_id} GROUP {event.group_id} "
                    f"花费 {need_money } 金币购买 {name} ×{num} 失败！"
                )
                await BagUser.add_gold(event.user_id,event.group_id,int(need_money))
