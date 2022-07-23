from .personal_goodsinfo import PersonalGoods
from utils.image_utils import BuildImage
from utils.utils import is_number
from configs.path_config import IMAGE_PATH
from typing import Union, Tuple
from configs.config import Config
from nonebot import Driver
from nonebot.plugin import require
from utils.decorator.shop import shop_register
import nonebot
import time

driver: Driver = nonebot.get_driver()


use = require("use")



@driver.on_bot_connect
async def _():
    await shop_register.load_register()


# 创建商店界面
async def create_shop_help() -> str:
    """
    制作商店图片
    :return: 图片base64
    """
    goods_lst = await PersonalGoods.get_all_goods()
    owner = await PersonalGoods.get_owner_qq()
    idx = 1
    _dc = {}
    font_h = BuildImage(0, 0).getsize("正")[1]
    h = 10
    _list = []
    for goods in goods_lst:
        if goods.goods_limit_time == 0 or time.time() < goods.goods_limit_time:
            h += len(goods.goods_description.strip().split("\n")) * font_h + 80
            _list.append(goods)
    A = BuildImage(1000, h, color="#f9f6f2")
    current_h = 0
    for goods in _list:
        bk = BuildImage(700, 80, font_size=15, color="#f9f6f2", font="CJGaoDeGuo.otf")
        goods_image = BuildImage(
            600, 80, font_size=20, color="#a29ad6", font="CJGaoDeGuo.otf"
        )
        name_image = BuildImage(
            580, 40, font_size=25, color="#e67b6b", font="CJGaoDeGuo.otf"
        )
        await name_image.atext(
            (15, 0), f"{idx}.{goods.goods_name}", center_type="by_height"
        )
        await name_image.aline((380, -5, 280, 45), "#a29ad6", 5)
        await name_image.atext((390, 0), "售价：", center_type="by_height")
        await name_image.atext(
            (440, 0), str(goods.goods_price), (255, 255, 255), center_type="by_height"
        )
        await name_image.atext(
            (
                440
                + BuildImage(0, 0, plain_text=str(goods.goods_price), font_size=25).w,
                0,
            ),
            " 金币",
            center_type="by_height",
        )
        await name_image.acircle_corner(5)
        await goods_image.apaste(name_image, (0, 5), True, center_type="by_width")
        idx += 1
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
        (int((1000 - shop.getsize("注【通过商品名称 购买】")[0]) / 2), 170),
        "注【通过商品名称 购买】",
    )
    shop.text(
        (int((1000 - shop.getsize(str({owner}))[0]) / 2), 170),
        str({owner}),
    )
    shop.text((20, h - 100), "交易时，有小真寻帮你看着哦！放心吧！")
    return shop.pic2bs4()


async def register_goods(
    name: str,
    owner:int,
    num: int,
    price: int,
    
) -> bool:
    """
    添加商品
    例如：                                                  
        #交易||#摆摊 name:[名称] num:[数量] price:[价格]
    :param name: 商品名称
    :param num: 商品数量
    :param price: 商品价格
    :return: 是否添加成功
    """
    if not await PersonalGoods.get_goods_info(owner,name):
        return await PersonalGoods.add_goods(
            name,owner,num, int(price)
        )
    return False


# 下架商品
async def delete_goods(name: str, owner:int,num: int) -> "str, int, int":
    """
    删除商品
    :param name: 商品名称
    :param num: 商品数量
    :return: 下架状况
    """
    if name:
        if await PersonalGoods.delete_goods(owner,name,num):
            return f"下架商品 {name} 共{num}成功！", name, num, 200
        else:
            return f"下架商品 {name} 共{num}失败！", name, num,999


# 更新商品信息
async def update_goods(**kwargs) -> Tuple[bool, str, str]:
    """
    更新商品信息
    :param kwargs: kwargs
    :return: 更新状况
    """
    if kwargs:
        if is_number(kwargs["name"]):
            return False,"这里是私人商店，没有id哦"
        else:
            goods = await PersonalGoods.get_goods_info(kwargs["name"])
            if not goods:
                return False, "名称错误，没有该名称的商品...", ""
        name: str = goods.goods_name
        owner_qq = goods.owner
        price = goods.goods_price
        tmp = ""
        if kwargs.get("price"):
            tmp += f'价格：{price} --> {kwargs["price"]}\n'
            price = kwargs["price"]
        await PersonalGoods.update_goods(
            owner_qq,
            name,
            int(price)
        )
        return True, name, tmp[:-1],


def parse_goods_info(msg: str) -> Union[dict, str]:
    """
    解析格式数据
    :param msg: 消息
    :return: 解析完毕的数据data
    """
    if "name:" not in msg:
        return "必须指定修改的商品名称或序号！"
    data = {}
    for x in msg.split():
        sp = x.split(":", maxsplit=1)
        if str(sp[1]).strip():
            sp[1] = sp[1].strip()
            if sp[0] == "name":
                data["name"] = sp[1]
            elif sp[0] == "price":
                if not is_number(sp[1]) or int(sp[1]) < 0:
                    return "price参数不合法，必须大于等于0！"
                data["price"] = sp[1]
            elif sp[0] == "num":
                if not is_number(sp[1]) or int(sp[1]) < 0:
                    return "num参数不合法，必须大于等于0！"
                data["num"] = sp[1]
    return data
