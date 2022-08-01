from re import T, X
from unicodedata import name
from nonebot import on_command,Driver
from services.log import logger
from nonebot.params import CommandArg
from nonebot.adapters.onebot.v11.permission import GROUP
from services.db_context import db
from nonebot.adapters.onebot.v11 import  GroupMessageEvent,Message
from configs.path_config import IMAGE_PATH
from utils.utils import  get_message_at, is_number
from utils.image_utils import BuildImage
from models.group_member_info import GroupInfoUser
from utils.message_builder import image
from models.bag_user import BagUser
from basic_plugins.shop.use.data_source import  func_manager
from configs.config import NICKNAME
from utils.utils import is_number
from models.goods_info import GoodsInfo
from ._personal_goodsinfo import func_text,PersonalGoods
import nonebot

__zx_plugin_name__="私人交易"
__plugin_usage__="""
usage:
    指令：
    创建私人商店||我要开店+[商品名]+[数量]+[价格]（加号处空格分割）
        示例：我要开店 好感度双倍加持卡Ⅰ 1 20
    看看他在卖什么||查看他的商店+艾特[目标]
        示例：看看他在卖什么 @弘涯
    下架||不想卖了+[商品名]+[数量]
        示例：下架 好感度双倍加持卡Ⅰ 1 
        示例：下架 4 1 (名称长度8字符及以上的商品使用代替id优化展示)
    修改私人商品||改价格+[商品名]+[价格]
        示例：改价格 好感度双倍加持卡Ⅰ 1
        示例：改价格 1 5  
""".strip()
__plugin_des__ = "创建私人商店"
__plugin_cmd__ = ["创建私人商店||我要开店+[商品名]+[数量]+[价格]（加号处空格分割）"]
__plugin_type__ = ("群内功能",)
__plugin_version__ = 9.1
__plugin_author__ = "十年"
__plugin_settings__ = {
    "level": 5,
    "default_status": True,
    "limit_superuser": False,
    "cmd": ["创建私人商店||我要开店+[商品名]+[数量]+[价格]（加号处空格分割）"]

}

driver: Driver = nonebot.get_driver()



cs=on_command("创建私人商店",aliases={"我要开店"},priority=5, block=True)

@cs.handle()
async def _(event: GroupMessageEvent, arg: Message = CommandArg()):
    """
    创建个人商品
    例如：
         #交易 堂主的readme.md 9999 1
    """
    uid = event.user_id
    group = event.group_id

    #遍历商店商品名字（检测售出商品是否为官方商店所有）
    goods_list = [
        x
        for x in await GoodsInfo.get_all_goods()
    ]
    goods_name_list = [
        x.goods_name
        for x in goods_list
    ]
    msg = arg.extract_plain_text().strip().split()
    num = 1
    fl= 0 #1为交易许可通过，0为未通过
    #此处为遍历用户背包
    goods_target = await BagUser.get_property(uid, group)
    #检测是否为商店所有
    # if len(msg_sp) > 1 and is_number(msg_sp[-1]) and int(msg_sp[-1]) > 0:
    #     num = int(msg.split()[-1])
    #     msg = " ".join(msg.split()[:-1])
    if msg[0] not in goods_name_list:
            #for i in range(len(goods_name_list)):
                #if msg[0] == goods_name_list[i]:
                    #goods = goods_list[i]
                    #break
    #else:
            await cs.finish("就你小子搁这想卖黑货是吧？",at_sender=True)

    #检测是否用户所有且上架的数量是否正确
    
    if msg[0] in goods_target:
        if len(msg[1]) > 0 and is_number(msg[1]):
            try:
                if int(msg[1]) > 0:
                        num = int(msg[1])
                        fl = 1
                        price = int(msg[2])
                else:
                        await cs.finish("上架的数量要大于0！", at_sender=True) 
            except ValueError as e:
                await cs.finish("你的奇怪数字是什么！请重新输入！！", at_sender=True)
        else:
                await cs.finish("请输入数字！", at_sender=True)
    else:
            await cs.finish(f"""你没有{msg[0]}啊\t要不先去小真寻这买点？""",at_sender=True)
    
    #创建私人商店
    if fl == 1:
            """
            删除拥有者背包道具
            """
            if len(msg) > 1 and is_number(msg[-2]) and int(msg[-2]) > 0:
                num = int(msg[-2])
                msg = " ".join(msg[:-1])
                msg = " ".join(msg.split()[:-1])#写的很丑是吧，我也觉得
            property_ = await BagUser.get_property(event.user_id, event.group_id)
            async with db.transaction():
                name = msg
                _user_prop_count = property_[name]
                if num > _user_prop_count:
                    await cs.finish(f"道具数量不足，无法上架{num}件！")
                if await BagUser.delete_property(event.user_id, event.group_id, name, num):
                    sucs = False#暂存一个标记，防止删除成功而上架失败导致商品消失（好像给真寻吞了也算正常……） 
                    if await func_text.add_goods_now(event.user_id,event.group_id,name,num,price):
                            sucs = True 
                            await cs.send(f"已从背包取出道具 {name}共 {num} 件并上架成功！", at_sender=True)
                            logger.info(
                        f"USER {event.user_id} GROUP {event.group_id} 上架道具 {name} {num} 件成功，单价为{price}"
                    )
                    #print(f'{func_manager.check_send_success_message(name)}  {await func_text.add_goods_now(event.user_id,event.group_id,name,num,price)}')
                    if sucs == False:
                            for i in range(num):
                                await BagUser.add_property(event.user_id,event.group_id,name)
                            await cs.send(f"已从背包取出道具 {name}共 {num} 件失败！{NICKNAME}已经将他们送回你的背包了", at_sender=True)
                            e = Exception
                            logger.error(
                        f" PersonalGoods add_goods 发生错误 {type(e)}：{e}"
                    )
                   # if msg := await effect(bot, event, name, num):
                       # await cs.send(msg, at_sender=True)
                       #logger.info(
                        #f"USER {event.user_id} GROUP {event.group_id} 已从背包取出道具 {name}共 {num} 件成功"
                #)
                else:
                    sucs = False
                    await cs.send(f"已从背包取出道具 {name}共 {num} 件失败！", at_sender=True)
                    logger.info(
                        f"USER {event.user_id} GROUP {event.group_id} 已从背包取出道具 {name}共 {num} 件失败！"
                )
    
cx = on_command("看看他在卖什么",aliases={"查看他的商店"},priority=5, block=True)
@cx.handle()
async def _(event: GroupMessageEvent, arg: Message = CommandArg()):
    """
    查看他人商店
    """
    qq = get_message_at(event.json())[0]
    uid = event.user_id
    group = event.group_id
    name = await GroupInfoUser.get_group_member_nickname(qq, group)
    if qq == uid:
        await cx.send(f"查询自己的商店可能会无法显示拥有人的哦~")
        logger.info(
            f'查看了自己的商店，无法显示某人的商店为正常现象'
        )
    text = ""
    if name == "":
        q = await GroupInfoUser.get_member_info(int(qq), group)
        if q:
            name = f'{q.user_name}'
        else:
            await cx.finish("出错了")
    text += f'{name}的商店'
    async def create_shop_help() -> str:
        """
        制作商店图片
        :return: 图片base64
        """
        goods_lst = await PersonalGoods.get_goods(qq,group)
        if goods_lst == {}:
            await cx.finish(f"没开店的人，看不到他的商店的哦")
        goods_n = 0
        for i in enumerate(goods_lst.keys()):
            goods_n += 1
        font_h = BuildImage(0, 0).getsize("正")[1]
        h = 10
        for _ in range(goods_n):
                h += len('私人商店'.strip().split("\n")) * font_h + 80
        A = BuildImage(1000, h, color="#f9f6f2")
        current_h = 0
        for i,p in enumerate(goods_lst.keys()):
            l = 0
            goods_name = p
            des = f'私人商店'
            goods_num = goods_lst[goods_name]['num']
            goods_price = goods_lst[goods_name]['price']
            #将超过8个字符的商品名放入简介中加以区分
            if len(goods_name) > 8 :
                des = f'{goods_name}'
                await PersonalGoods.add_than_8_goods_now(qq,group,goods_name,str(i+1),goods_num,goods_price)
                goods_re = await PersonalGoods.get_replace_goods(qq,group)
                goods_name = goods_re[str(i+1)]['id']
            bk = BuildImage(700, 80, font_size=15, color="#f9f6f2", font="CJGaoDeGuo.otf")
            goods_image = BuildImage(
                    600, 80, font_size=20, color="#a29ad6", font="CJGaoDeGuo.otf"
                )
            name_image = BuildImage(
                    580, 40, font_size=25, color="#e67b6b", font="CJGaoDeGuo.otf"
                )
            await name_image.atext(
                    (15, 0), f"{i+1}.{goods_name}", center_type="by_height"
                )
            await name_image.aline((380, -5, 280, 45), "#a29ad6", 5)
            await name_image.atext((200, 0), "余量：", center_type="by_height")
            await name_image.atext(
                    (250, 0), f"{goods_num}", center_type="by_height"
                )
            await name_image.atext((390, 0), "售价：", center_type="by_height")
            await name_image.atext(
                    (440, 0), str(goods_price), (255, 255, 255), center_type="by_height"
                )
            await name_image.atext(
                    (
                        440
                        + BuildImage(0, 0, plain_text=str(goods_price), font_size=25).w,
                        0,
                ),
                " 金币",
                center_type="by_height",
            )
            await name_image.acircle_corner(5)
            await goods_image.apaste(name_image, (0, 5), True, center_type="by_width")
            await goods_image.atext((15, 50), f"简介：{des}")
            await goods_image.acircle_corner(20)
            await bk.apaste(goods_image, alpha=True)
            await A.apaste(bk, (0, current_h), True)
            current_h += 90
        w = 1000
        h = A.h + 230 + 100
        h = 1000 if h < 1000 else h
        shop_logo = BuildImage(100, 100, background=f"{IMAGE_PATH}/other/shop_text.png")
        shop = BuildImage(w, h, font_size=20, color="#f9f6f2")
        shop.paste(A, (20, 230))
        zx_img = BuildImage(0, 0, background=f"{IMAGE_PATH}/zhenxun/toukan.png")
        zx_img.replace_color_tran(((240, 240, 240), (255, 255, 255)), (249, 246, 242))
        await shop.apaste(zx_img, (780, 100))
        await shop.apaste(shop_logo, (450, 30), True)
        shop.text(
            (int((1000 - shop.getsize(f"拥有人：{name}")[0]) / 2), 125),
            f"拥有人：{name}",
        )
        shop.text(
            (int((1000 - shop.getsize("注【通过 商品名称 购买】")[0]) / 2), 170),
            "注【通过 商品名称 购买】",
        )
        shop.text((20, h - 100), "交易过程中，都会有小真寻看着的，放心吧~")
        return shop.pic2bs4() 
    await cx.send(text+image(b64=await create_shop_help()), at_sender=True)
    
xj = on_command('下架',aliases={"不想卖了"},priority=5, block=True)
@xj.handle()
async def _(event: GroupMessageEvent, arg: Message = CommandArg()):
    """
    下架商品
    """
    uid = event.user_id
    group = event.group_id
    goods_lst = await PersonalGoods.get_goods(uid,group)
    goods_name_list = []
    for i,p in enumerate(goods_lst.keys()):
        goods_name_list.append(p)

    msg = arg.extract_plain_text().strip().split()
    num = 0
    f1 = 0
    i = 0
    if is_number(msg[0]):
        goods_name_lst = await PersonalGoods.get_replace_goods(uid,group)
        if  goods_name_lst == {}:
            await cs.finish(f"代替id打错了，或是你的商店里没有这个商品哦",at_sender=True)
        name = goods_name_lst[msg[0]]['name']
    else:
        name = msg[0]
        if msg[0] not in goods_name_list:
            await cs.finish(f"你的商店里没有 {name} 这个商品哦",at_sender=True)
       
    if len(msg[1]) > 0 and is_number(msg[1]):
        try:
            if int(msg[1]) > 0:
                            num = int(msg[1])
                            f1 = 1
            else:
                            await cs.finish("下架的数量要大于0！", at_sender=True) 
        except ValueError as e:
                    await cs.finish("你的奇怪数字是什么！请重新输入！！", at_sender=True)
    if f1 == 1:
        g = goods_lst[name]['num']
        if num > g :
            await xj.finish(f'超出商品上限！您的商店里明明只有 {g} 件 {name} ！')
        if await PersonalGoods.change_goods_now(uid,group,name,num) :
            for _ in range(num):
                await BagUser.add_property(uid,group,name)
                i += 1 
            if i == num:
                await xj.finish(f'下架 {name} 共 {num} 件成功！')
            else:
                await xj.finish(f'下架 {name} 共 {num} 件失败！')
        else :
            await xj.finish(f"该商品 {name} 已经清空，无法下架啦")

xg = on_command('修改私人商品',aliases={'改价格'},priority=5, block=True)
@xg.handle()
async def _(event: GroupMessageEvent, arg: Message = CommandArg()):
    """
    修改商品价格
    """
    uid = event.user_id
    group = event.group_id
    goods_lst = await PersonalGoods.get_goods(uid,group)
    goods_name_list = []
    for i,p in enumerate(goods_lst.keys()):
        goods_name_list.append(p)

    msg = arg.extract_plain_text().strip().split()
    price = 0
    f1 = 0
    i = 0
    if is_number(msg[0]):
        goods_name_lst = await PersonalGoods.get_replace_goods(uid,group)
        if  goods_name_lst == {}:
            await cs.finish(f"代替id打错了，或是你的商店里没有这个商品哦",at_sender=True)
        name = goods_name_lst[msg[0]]['name']
    else:
        name = msg[0]
        if name not in goods_name_list:
            await cs.finish(f"你的商店里没有 {name} 这个商品哦",at_sender=True)
    
    if len(msg[1]) > 0 and is_number(msg[1]):
        try:
            if int(msg[1]) > 0:
                    price = int(msg[1])
                    f1 = 1
            else:
                    await cs.finish("修改商品的价格要大于0！", at_sender=True) 
        except ValueError as e:
                await cs.finish("你的奇怪数字是什么！请重新输入！！", at_sender=True)
    if f1 == 1:
        if await PersonalGoods.add_goods_now(uid,group,name,0,price) :
                await xj.finish(f'已将 {name} 的价格修改为{price}成功！')
        else :
            await xj.finish(f"该商品 {name} 已经清空，无法修改价格啦")