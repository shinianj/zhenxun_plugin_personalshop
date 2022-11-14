from ast import Str
from re import M, T, X
from tkinter.tix import Tree
from turtle import Turtle
from typing import  Dict, Tuple,Any,Union
from nonebot import on_command,Driver,on_regex
from services.log import logger
from nonebot.params import CommandArg,RegexGroup
from nonebot.adapters.onebot.v11.permission import GROUP
from services.db_context import db
from nonebot.adapters.onebot.v11 import  GroupMessageEvent,Message,ActionFailed
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
import time
from utils.utils import scheduler, get_bot
from datetime import datetime

__zx_plugin_name__="私人交易"
__plugin_usage__="""
usage:
    指令：
    创建私人商店||我要开店+[商品名]+[数量]+[价格]+[描述]+[折扣]+[上架限时时间]+[折扣限时时间]+[每日购买限制次数]+[购买条件]（加号处空格分割）
        示例：我要开店 好感度双倍加持卡Ⅱ 1 20 我的天 0.4 2 1 2 金币大于100_权限管理员
              我要开店 好感度双倍加持卡Ⅱ num:1 price:20 des:我的天 dis:0.4 addlim:2 dislim:1 daylim:2 lim:金币大于100_权限管理员
              我要开店 好感度双倍加持卡Ⅱ 数量:1 价格:20 描述:我的天 折扣:0.4 上架限时:2 折扣限时:1 每日购买:2 购买条件:金币大于100_权限管理员
            (必需值为名字，数量，价格)
    看看他在卖什么||查看他的商店+艾特[目标]
        示例：看看他在卖什么 @弘涯
    (一键)?下架+[商品名|所有商品]+[数量]
        示例：下架好感度双倍加持卡Ⅰ 1 
              一键下架好感度双倍加持卡Ⅰ
              下架所有商品 1 
              一键下架所有商品
    修改私人商品||改价格+[商品名]+[价格]+[描述]+[折扣]+[上架限时时间]+[折扣限时时间]+[每日购买限制次数]+[购买条件]
        示例：改商品|修改私人商品 好感度双倍加持卡Ⅰ num:1 
              改商品|修改私人商品 好感度双倍加持卡Ⅰ price:20
""".strip()
__plugin_des__ = "创建私人商店"
__plugin_cmd__ = ["创建私人商店||我要开店+[商品名]+[数量]+[价格]（加号处空格分割）"]
__plugin_type__ = ("群内功能",)
__plugin_version__ = 0.1
__plugin_author__ = "十年"
__plugin_settings__ = {
    "level": 5,
    "default_status": True,
    "limit_superuser": False,
    "cmd": ["创建私人商店||我要开店+[商品名]+[数量]+[价格]（加号处空格分割）"]

}
icon_path = IMAGE_PATH / 'shop_icon'

async def add_limit(need:str)-> dict:
    '''
    说明：
        添加购买限制条件
    参数：
        :param need:条件
    '''
    limit = {}
    com = need.strip().split('_')
    for i in com:
        if '金币' in i or 'gold' in i:
            i = i.replace('金币','')if '金币' in i else i.replace('gold','')
            gold_ = i.strip().split('金')
            for g in gold_:
                if '大于' in g or '>' in g:
                    i = i.replace('大于',' ')if '大于' in i else i.replace('>',' ')
                    
                    limit['dayu_gold'] = i.strip().split()[0]
                if '小于' in i or '<' in i:
                    i = i.replace('小于',' ')if '小于' in i else i.replace('<',' ')
                    limit['xiaoyu_gold'] = i.strip().split()[0]
        if '权限' in i or 'power' in i:
            i = i.replace('权限','')if '权限' in i else i.replace('power','')
            if '管理员' in i:
                limit['permission'] = 'administrators'

    return limit


async def limit_info(lim:dict)-> str:
    '''
    说明：
        商品限制条件解读
    参数：
        :param lim:商品条件字典
    '''
    if lim != {}:
        result = '限定'
        f1 = 0
        f2 = 0
        for i,p in enumerate(lim.keys()):
            if p == 'dayu_gold':
                result += '金币大于'+lim[p]
                f1 = 1 
            if p == 'xiaoyu_gold':
                if f1 == 1:
                    result += '且小于' + lim[p]
                else:
                    result += '金币小于' + lim[p]
            if p == 'permission':
                if lim[p] == 'administrators':
                    result+='权限为管理员'
        result += '的用户'
        return result
    else:
        return '无限制'

async def goods_info(
        msg:Message,
        num:int = 1,
        price:int = 0,
        description: str = '无',
        limit :dict = {},
        discount: float = 1,
        discount_limit_time: str = '0',
        add_limit_time: str = '0',
        daily_limit: int = 0,
        add : bool = True)-> Union[str,dict]:
    '''
    说明：
        添加/修改 商品执行判断
    参数：

                :param name: 商品名称
                :param num: 上架数量
                :param price: 商品价格
                :param description: 商品描述
                :param limit: 购买该商品条件
                :param discount: 商品折扣
                :param discount_limit_time: 商品折扣限时
                :param add_limit_time: 商品上架限时
                :param daily_limit: 每日购买限制
                :param add: 是否为添加操作
    '''
    msg_ = msg.extract_plain_text().strip().split()

    name = msg_[0]
    today = datetime.now()
    log = '' #结果log
    range_log = '添加错误，以下部分有输入问题:\n'#范围log
    error_log ='商品的' #报错log
    nes = {'name':True,'num':False,'price':False} #必要三要素检测：name,num,price
    if add == False:
        nes = {'name':True,'num':True,'price':True} 
    result = {'name':name,'num':num,'price':price,'des':description,'lim':limit,'dis':discount,'dis_lim':discount_limit_time,'add_lim':add_limit_time,'day_lim':daily_limit} #返回字典
    f1 = False #是否通过指定名称输入
    f2 = True #输入格式判断（错误为False)
    f3 = True #输入数值范围判断(错误为Flase)
    for i in range(1,len(msg_)):
            if '数量' in msg_[i] or 'num' in msg_[i]:
                num_ = str(msg_[i]).strip().split(':')[1]
                if len(num_) > 0 and is_number(num_):
                    try:
                        if int(num_) > 0:
                                num = int(num_)
                                log += f'数量为 {num} '
                                result['num']=num
                                nes['num']=True
                        else:
                                f3 = False
                                range_log+= "[num]"
                    except ValueError as e:
                        error_log+=(f"[num] {e}\n")
                        f2 = False
                        pass
            elif '价格' in msg_[i] or 'price' in msg_[i]:
                price_ = str(msg_[i]).strip().split(':')[1]
                if len(price_) > 0 and is_number(price_):
                    try:
                        if int(price_) > 0:
                                price = int(price_)
                                log += f'价格为 {price} '
                                result['price']=price
                                nes['price']=True
                        else:
                                f3 = False
                                range_log+= "[price]"
                    except ValueError as e:
                        error_log+=(f"[price] {e}\n")
                        f2 = False
                        pass
            elif '描述' in msg_[i] or 'des' in msg_[i]:
                des_ = str(msg_[i]).strip().split(':')[1]
                if len(des_) > 10:
                    f3 = False
                    range_log+=("[描述太长，最多十个字符]")
                else:
                    des = des_
                    result['des']=des
                    log += f'描述改为 {des} '
            elif '折扣' in msg_[i] or 'dis' in msg_[i]:
                dis_ = (msg_[i]).strip().split(':')[1]
                if len(dis_) > 0 and is_number(dis_):
                    dis_ = float(dis_)
                    try:
                        if (dis_) > 0:
                                dis = (dis_)
                                log += f'折扣为 {dis} '
                                result['dis']=dis
                        else:
                                f3 = False
                                range_log+= "[dis]"
                    except ValueError as e:
                        error_log+=(f"[dis] {e}\n")
                        f2 = False
                        pass
            elif '上架限时' in msg_[i] or 'addlim' in msg_[i]:
                add_lim_ = str(msg_[i]).strip().split(':')[1]
                if len(add_lim_) > 0 and is_number(add_lim_):
                    try:
                        if int(add_lim_) > 0:
                                add_lim = int(add_lim_)
                                y_m_d,h_m = time_add(today,add_lim)
                                y_m_d_h_m = y_m_d+h_m
                                log += f'上架限时为 {add_lim} 小时'
                                result['add_lim']=y_m_d_h_m
                        else:
                                f3 = False
                                range_log+= "[add_lim]"
                    except ValueError as e:
                        error_log+=(f"[add_lim] {e}\n")
                        f2 = False
                        pass
            elif '折扣限时' in msg_[i] or 'dislim' in msg_[i]:
                dis_lim_ = str(msg_[i]).strip().split(':')[1]
                if len(dis_lim_ ) > 0 and is_number(dis_lim_ ):
                    try:
                        if int(dis_lim_) > 0:
                                dis_lim = int(dis_lim_) 
                                y_m_d,h_m = time_add(today,add_lim)
                                y_m_d_h_m = y_m_d+h_m
                                log += f'折扣限时为 {dis_lim} 小时'
                                result['dis_lim']= y_m_d_h_m
                        else:
                                f3 = False
                                range_log+= "[dis_lim]" 
                    except ValueError as e:
                        error_log+=(f"[dis_lim] {e}\n")
                        f2 = False
                        pass
            elif '每日购买' in msg_[i] or 'daylim' in msg_[i]:
                day_lim_ = str(msg_[i]).strip().split(':')[1]
                if len(day_lim_ ) > 0 and is_number(day_lim_ ):
                    try:
                        if int(day_lim_ ) > 0:
                                day_lim = int(day_lim_ )
                                log += f'每日购买限制为 {day_lim} '
                                result['day_lim']=day_lim
                        else:
                                f3 = False
                                range_log+= "[day_lim]" 
                    except ValueError as e:
                        error_log+=(f"[day_lim] {e}\n")
                        f2 = False
                        pass
            elif '购买条件' in msg_[i] or 'lim' in msg_[i]:
                lim_ = str(msg_[i]).strip().split(':')[1]
                if '金币' in lim_ or 'gold' in lim_ or '权限' in lim_ or 'power' in lim_ :
                    lim = str(lim_)
                    log += f'购买条件为 {lim} '
                    result['lim']=await add_limit(lim)
                else:
                    f2 = False
                    error_log+=("[lim]")

    if result == {'name':name,'num':num,'price':price,'des':description,'lim':limit,'dis':discount,'dis_lim':discount_limit_time,'add_lim':add_limit_time,'day_lim':daily_limit} :
        #未检测到关键字添加，采取按位置自动添加
        for i in range(1,len(msg_)):

            #这块写的真差劲（痛骂自己）
            if i == 1:
                num_ = str(msg_[i]).strip()
                if len(num_) > 0 and is_number(num_):
                    try:
                        if int(num_) > 0:
                                num = int(num_)
                                log += f'数量为 {num} '
                                result['num']=num
                                nes['num']=True
                        else:
                                f3 = False
                                range_log+= "[num]"
                    except ValueError as e:
                        error_log+=(f"[num] {e}\n")
                        f2 = False
                        pass
            elif i == 2:
                price_ = str(msg_[i]).strip()
                if len(price_) > 0 and is_number(price_):
                    try:
                        if int(price_) > 0:
                                price = int(price_)
                                log += f'价格为 {price} '
                                result['price']=price
                                nes['price']=True
                        else:
                                f3 = False
                                range_log+= "[price]"
                    except ValueError as e:
                        error_log+=(f"[price] {e}\n")
                        f2 = False
                        pass
            elif i == 3:
                des_ = str(msg_[i]).strip()
                if len(des_) > 10:
                    f3 = False
                    range_log+=("[描述太长，最多十个字符]")
                else:
                    des = des_
                    result['des']=des
                    log += f'描述为 {des} '
            elif i == 4:
                dis_ = msg_[i]
                if len(dis_) > 0 and is_number(dis_):
                    dis_ = float(dis_)
                    try:
                        if dis_ > 0:
                                dis = dis_
                                log += f'折扣为 {dis} '
                                result['dis']=dis
                        else:
                                f3 = False
                                range_log+= "[dis]"
                    except ValueError as e:
                        error_log+=(f"[dis] {e}\n")
                        f2 = False
                        pass
            elif i == 5:
                add_lim_ = str(msg_[i]).strip()
                if len(add_lim_) > 0 and is_number(add_lim_):
                    try:
                        if int(add_lim_) > 0:
                                add_lim = int(add_lim_)
                                y_m_d,h_m = time_add(today,add_lim)
                                y_m_d_h_m = y_m_d+h_m
                                log += f'上架限时为 {add_lim} 小时'
                                result['add_lim']=y_m_d_h_m
                        else:
                                f3 = False
                                range_log+= "[add_lim]"
                    except ValueError as e:
                        error_log+=(f"[add_lim] {e}\n")
                        f2 = False
                        pass
            elif i == 6:
                dis_lim_ = str(msg_[i]).strip()
                if len(dis_lim_ ) > 0 and is_number(dis_lim_ ):
                    try:
                        if int(dis_lim_) > 0:
                                dis_lim = int(dis_lim_) 
                                y_m_d,h_m = time_add(today,dis_lim)
                                y_m_d_h_m = y_m_d+h_m
                                log += f'折扣限时为 {dis_lim} 小时'
                                result['dis_lim']= y_m_d_h_m
                        else:
                                f3 = False
                                range_log+= "[dis_lim]" 
                    except ValueError as e:
                        error_log+=(f"[dis_lim] {e}\n")
                        f2 = False
                        pass
            elif i == 7:
                day_lim_ = str(msg_[i]).strip()
                if len(day_lim_ ) > 0 and is_number(day_lim_ ):
                    try:
                        if int(day_lim_ ) > 0:
                                day_lim = int(day_lim_ )
                                log += f'每日购买限制为 {day_lim} '
                                result['day_lim']=day_lim
                        else:
                                f3 = False
                                range_log+= "[day_lim]" 
                    except ValueError as e:
                        error_log+=(f"[day_lim] {e}\n")
                        f2 = False
                        pass
            elif i == 8:
                lim_ = str(msg_[i]).strip()
                if '金币' in lim_ or 'gold' in lim_ or '权限' in lim_ or 'power' in lim_ :
                    lim = str(lim_)
                    log += f'购买条件为 {lim} '
                    result['lim']=await add_limit(lim)
                else:
                    f2 = False
                    error_log+=("[lim]")


        if f2 == False:
            #报错优先返回
            error_log += '有报错，请检查'
            return error_log
        for i in nes:
            if nes[i] == False:
                return f'缺少必要值{i} '
        if f3 == False:
            #数据范围错误
            return range_log

        result['log'] = log

        return result
        
def time_add(today,add_hours)->Tuple[str,str]:
    '''
    计算限时时间
    :param today: 当前时间
    :param add_hours: 加上的时间
    '''
    limit_time = today.strftime(
                    "%Y-%m-%d %H:%M"
                ).split()
    y = int(limit_time[0].split("-")[0])
    mou = int(limit_time[0].split("-")[1])
    d = int(limit_time[0].split("-")[2])
    list=[31,28,31,30,31,30,31,31,30,31,30,31]
    if int(y)%400==0 or int(y)%4 == 0 and int(y)%100!=0:
            list[1]=29
    mouth_max = list[(mou)-1]
    _h_m = limit_time[1].split(":")
    h = int(_h_m[0])
    m = _h_m[1]
    h += add_hours
    if h >= 24 :
        n = 0
        while h >= 24:
            h -= 24
            n +=1
        d += n
        if d > mouth_max:
            while d > mouth_max:
                d -= mouth_max
                mou += 1
                if mou > 12:
                    while mou > 12:
                        mou -= 12
                        y += 1
                mouth_max = list[mou-1]
        
    y_m_d = f'{y}-{mou}-{d}-'
    h_m = f'{h}时{m}分'
    return y_m_d , h_m           

def fen(y_m_d_h_m) -> Tuple[int,int,int,int,int]:
    '''
    分离年月日
    :param y_m_d: 年月日
    :param h_m: 时分
    '''
    h_m_= y_m_d_h_m.replace('时','-')
    h_m_= h_m_.replace('分','-')
    y = h_m_.split("-")[0]
    mou = h_m_.split("-")[1]
    d = h_m_.split("-")[2]
    h = h_m_.split("-")[3]
    m = h_m_.split("-")[4]
    return y,mou,d,h,m

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
    goods = await goods_info(arg)

    goods_in = {}
    if msg[0] in goods_target:
        if isinstance(goods,str):
            await cs.finish(f'{goods}',at_sender=True)
        elif isinstance(goods,dict):
            goods_in = goods
            fl =1
    else:
            await cs.finish(f"""你没有{msg[0]}啊\t要不先去小真寻这买点？""",at_sender=True)

    num = goods_in['num']
    price = goods_in['price']
    des = goods_in['des']
    limit = goods_in['lim']
    discount= goods_in['dis']
    discount_limit_time = goods_in['dis_lim']
    add_limit_time = goods_in['add_lim']
    daily_limit = goods_in['day_lim']
    log = goods_in['log']
    #创建私人商店
    if fl == 1:
            """
            删除拥有者背包道具
            """
            # if len(msg) > 1 and is_number(msg[-2]) and int(msg[-2]) > 0:
            #     num = int(msg[-2])
            #     msg = " ".join(msg[:-1])
            #     msg = " ".join(msg.split()[:-1])#写的很丑是吧，我也觉得
            property_ = await BagUser.get_property(event.user_id, event.group_id)
            async with db.transaction():
                name = msg[0]
                ###
                _user_prop_count = property_[name]
                if num > _user_prop_count:
                    await cs.finish(f"道具数量不足，无法上架{num}件！")
                if await BagUser.delete_property(event.user_id, event.group_id, name, num):
                    sucs = False#暂存一个标记，防止删除成功而上架失败导致商品消失（好像给真寻吞了也算正常……） 
                    if await func_text.add_goods_now(event.user_id,event.group_id,name,num,price,des,limit,discount,discount_limit_time,add_limit_time,daily_limit):
                            sucs = True 
                            await cs.send(f"已从背包取出道具 {name}共 {num} 件并上架成功！", at_sender=True)
                            logger.info(
                        f"USER {event.user_id} GROUP {event.group_id} 上架道具 {name} {num} 件成功，单价为{price}"
                    )
                    logger.info(
                        f"USER {event.user_id} GROUP {event.group_id} 上架道具 {name} {log}成功"
                    )
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
        await cx.send(f"查询自己的商店会无法显示拥有人的哦~")
        logger.info(
            f'查看了自己的商店，无法显示某人的商店为正常现象'
        )
    text = ""
    if name == "":
        q = await GroupInfoUser.get_member_info(int(qq), group)
        if q:
            name = f'{q.user_name}'
    text += f'{name}的商店'
    async def create_shop_help() -> str:
        """
        制作商店图片
        :return: 图片base64
        """
        idx = 1
        shop_goods_ls = await GoodsInfo.get_all_goods()
        goods_lst = await PersonalGoods.get_goods(qq,group)
        
        if goods_lst == {}:
            await cx.finish(f"没开店的人，看不到他的商店的哦")
        goods_n = 0
        for i in enumerate(goods_lst.keys()):
            goods_n += 1
        font_h = BuildImage(0, 0).getsize("正")[1]
        h = 10
        _list = []
        for _ in range(goods_n):
                h += len('私人商店'.strip().split("\n")) * font_h + 80
        for goods in shop_goods_ls:
            if goods.goods_limit_time == 0 or time.time() < goods.goods_limit_time:
                _list.append(goods)
        A = BuildImage(1000, h, color="#f9f6f2")
        current_h = 0
        total_n = 0
        for i,p in enumerate(goods_lst.keys()):
            goods_name = p
            goods_num = goods_lst[goods_name]['num']
            goods_price = goods_lst[goods_name]['price']
            goods_des = goods_lst[goods_name]['description']
            goods_dis = goods_lst[goods_name]['discount']
            goods_dis_lim = goods_lst[goods_name]['discount_limit_time']
            goods_add_lim = goods_lst[goods_name]['add_limit_time']
            goods_lim = goods_lst[goods_name]['limit']
            goods_day_lim = goods_lst[goods_name]['daily_limit']
            bk = BuildImage(1180, 80, font_size=15, color="#f9f6f2", font="CJGaoDeGuo.otf")
            for g in _list:
                if goods_name == g.goods_name :
                    if (icon_path / g.icon).exists() and g.icon:
                        goods_icon = g.icon
                        icon = BuildImage(100, 100, background=icon_path / goods_icon)
                        await bk.apaste(icon)
            goods_image = BuildImage(
                    600, 80, font_size=20, color="#a29ad6", font="CJGaoDeGuo.otf"
                )
            if len(goods_name) > 8:
                goods_name = goods_name[0:8]
            goods_info = ''
            goods_info += goods_name
            # if goods_lim :
            #     goods_info += await limit_info(goods_lim)
            name_image = BuildImage(
                    580, 40, font_size=25, color="#e67b6b", font="CJGaoDeGuo.otf"
                )
            limit_image = BuildImage(
                    580, 13, font_size=13, color="#a29ad6", font="CJGaoDeGuo.otf"
                )
            await name_image.atext(
                    (15, 0), f"{idx}.{goods_info}", center_type="by_height"
                )
            await name_image.aline((380, -5, 280, 45), "#a29ad6", 5)
            await name_image.atext((200, 0), "余量：", center_type="by_height")
            await name_image.atext(
                    (250, 0), f"{goods_num}", center_type="by_height"
                )
            await name_image.atext((390, 0), "售价：", center_type="by_height")
            # await name_image.atext(
            #         (440, 0), str(goods_price), (255, 255, 255), center_type="by_height"
            #     )
            if goods_dis != 1:
                discount_price = int(goods_dis * goods_price)
                old_price_image = BuildImage(0, 0, plain_text=str(goods_price), font_color=(194, 194, 194), font="CJGaoDeGuo.otf", font_size=15)
                await old_price_image.aline((0, int(old_price_image.h / 2), old_price_image.w + 1, int(old_price_image.h / 2)), (0, 0, 0))
                await name_image.apaste(
                    old_price_image, (440, 0), True
                )
                await name_image.atext(
                    (440, 15), str(discount_price), (255, 255, 255)
                )
            else:
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
            await goods_image.atext((15, 50), f"简介：{goods_des}")
            await limit_image.atext((5, 0), await limit_info(goods_lim),fill = '#C60000')
            await goods_image.apaste(limit_image, (15, 67), True, center_type="by_width")
            # 添加限时上架
            if goods_add_lim != '0' :
                
                y,mou,d,h,m = fen(goods_add_lim)
                y_m_d = f'{y}-{mou}-{d}'
                h_m = f' {h} 时 {m} 分'
                
                await goods_image.atext((200, 50), f"限时上架！到 {y_m_d} {h_m }为止！",fill = '#C60000')
            await goods_image.acircle_corner(20)
            await bk.apaste(goods_image, (100, 0),alpha=True)
            n = 0
            _w = 650
                # 添加限时图标和时间
            if goods_dis_lim != '0':
                n += 140
                _limit_time_logo = BuildImage(
                    40, 40, background=f"{IMAGE_PATH}/other/time.png"
                )
                await bk.apaste(_limit_time_logo, (_w + 50, 0), True)
                await bk.apaste(
                    BuildImage(0, 0, plain_text="限时！", font_size=23, font="CJGaoDeGuo.otf"),
                    (_w + 90, 10),
                    True,
                )
                y,mou,d,h,m = fen(goods_dis_lim)
                y_m_d = f'{y}-{mou}-{d}'
                h_m = f' {h} 时 {m} 分'
                await bk.atext((_w + 55, 38), str(y_m_d))
                await bk.atext((_w + 65, 57), str(h_m))
                _w += 140
            if goods_dis != 1:
                n += 140
                _discount_logo = BuildImage(30, 30, background=f"{IMAGE_PATH}/other/discount.png")
                await bk.apaste(_discount_logo, (_w + 50, 10), True)
                await bk.apaste(
                    BuildImage(0, 0, plain_text="折扣！", font_size=23, font="CJGaoDeGuo.otf"),
                    (_w + 90, 15),
                    True,
                )
                await bk.apaste(
                    BuildImage(0, 0, plain_text=f"{10 * goods_dis:.1f} 折", font_size=30, font="CJGaoDeGuo.otf", font_color=(85, 156, 75)),
                    (_w + 50, 44),
                    True,
                )
                _w += 140
            if goods.daily_limit != 0:
                n += 140
                _daily_limit_logo = BuildImage(35, 35, background=f"{IMAGE_PATH}/other/daily_limit.png")
                await bk.apaste(_daily_limit_logo, (_w + 50, 10), True)
                await bk.apaste(
                    BuildImage(0, 0, plain_text="限购！", font_size=23, font="CJGaoDeGuo.otf"),
                    (_w + 90, 20),
                    True,
                )
                await bk.apaste(
                    BuildImage(0, 0, plain_text=f"{goods.daily_limit}", font_size=30, font="CJGaoDeGuo.otf"),
                    (_w + 72, 45),
                    True,
                )
            if total_n < n:
                total_n = n
            if n:
                await bk.aline((650, -1, 650 + n, -1), "#a29ad6", 5)
                await bk.aline((650, 80, 650 + n, 80), "#a29ad6", 5)

            idx += 1
            await A.apaste(bk, (0, current_h), True)
            current_h += 90
        w = 950
        if total_n:
            w += total_n
            h = A.h + 230 + 100
        h = 1000 if h < 1000 else h
        shop_logo = BuildImage(100, 100, background=f"{IMAGE_PATH}/other/shop_text.png")
        shop = BuildImage(w, h, font_size=20, color="#f9f6f2")
        shop.paste(A, (20, 230))
        zx_img = BuildImage(0, 0, background=f"{IMAGE_PATH}/zhenxun/toukan.png")
        zx_img.replace_color_tran(((240, 240, 240), (255, 255, 255)), (249, 246, 242))
        await shop.apaste(zx_img, (960, 100))
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
    
xj = on_regex(r'^(一键)?下架(所有商品|.*)?$',priority=5, block=True)
@xj.handle()
async def _(event: GroupMessageEvent, ev: Tuple[Any, ...] = RegexGroup()):
    """
    下架商品
    """
    
    uid = event.user_id
    group = event.group_id
    goods_lst = await PersonalGoods.get_goods(uid,group)
    goods_name_list = []
    for i,p in enumerate(goods_lst.keys()):
        goods_name_list.append(p)

    msg = ''
    name = ''
    num = 1
    
    if  ev[1] != '所有商品':
        msg = ev[1].split()
        name = msg[0]
        if not ev[0]:
            num = int(msg[1])
    f1 = 0
    i = 0
    if name not in goods_name_list and  '所有商品' not in ev[1]:
        await xj.finish(f"你的商店里没有 {name} 这个商品哦",at_sender=True)
    elif name  in goods_name_list or ev[1] == '所有商品':
        if '所有商品'  in ev[1]:
            for k in goods_name_list:
                name = k
                num_= ev[1].replace('所有商品',' ')
                g = goods_lst[name]['num']
                if ev[0]:
                        num = g
                        f1 = 1
                else:
                    if int(num_) > 0 and is_number(int(num_)):
                        num = int(num_)
                        f1 = 1
                if f1 == 1:
                        if num > g :
                            await xj.finish(f'超出商品上限！您的商店里明明只有 {g} 件 {name} ！')
                        if await PersonalGoods.change_goods_now(uid,group,name,num) :
                                for _ in range(num):
                                    await BagUser.add_property(uid,group,name)
                                    i += 1 
                                if i == num:
                                    await xj.send(f'下架 {name} 共 {num} 件成功！')
                                else:
                                    await xj.finish(f'下架 {name} 共 {num} 件失败！')
                        else :
                                await xj.send(f"该商品 {name} 已经清空，无法下架啦") 
        else:
            g = goods_lst[name]['num']
            if ev[0]:
                    num = g
                    f1 =1
            else:
                if len(num) > 0 and is_number(num):
                    try:
                        if int(num) > 0:
                                f1 = 1
                        else:
                                await xj.finish("下架的数量要大于0！", at_sender=True) 
                    except ValueError as e:
                        await xj.finish("你的奇怪数字是什么！请重新输入！！", at_sender=True)
            if f1 == 1:
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


xg = on_command('修改私人商品',aliases={'改商品'},priority=5, block=True)
@xg.handle()
async def _(event: GroupMessageEvent, arg: Message = CommandArg()):
    """
    修改商品信息
    """
    uid = event.user_id
    group = event.group_id
    goods_lst = await PersonalGoods.get_goods(uid,group)
    goods_name_list = []
    for i,p in enumerate(goods_lst.keys()):
        goods_name_list.append(p)

    msg = arg.extract_plain_text().strip().split()
    price = 0
    log = ''
    if msg[0] not in goods_name_list:
        await xg.finish("你的商店里没有这个商品哦",at_sender=True)
    else:
        price = goods_lst[msg[0]]['price']
        des = goods_lst[msg[0]]['description']
        dis = goods_lst[msg[0]]['discount']
        lim = goods_lst[msg[0]]['limit']
        dis_lim = goods_lst[msg[0]]['discount_limit_time']
        add_lim = goods_lst[msg[0]]['add_limit_time']
        day_lim = goods_lst[msg[0]]['daily_limit']
        # for i in range(1,len(msg)):
        #     if '价格' in msg[i] or 'price' in msg[i]:
        #         price_ = str(msg[i]).strip().split(':')[1]
        #         if len(price_) > 0 and is_number(price_):
        #             try:
        #                 if int(price_) > 0:
        #                         price = int(price_)
        #                         f1 = 1
        #                         log += f'价格修改为 {price} '
        #                 else:
        #                         await xg.finish("修改商品的价格要大于0！", at_sender=True) 
        #             except ValueError as e:
        #                 await xg.finish("[price]你的奇怪数字是什么！请重新输入！！", at_sender=True)
        #     elif '描述' in msg[i] or 'des' in msg[i]:
        #         des_ = str(msg[i]).strip().split(':')[1]
        #         if len(des) > 10:
        #             await xg.finish("描述太长，最多十个字符哦！", at_sender=True)
        #         des = des_
        #         f1 = 1
        #         log += f'描述改为 {des} '
        #     elif '折扣' in msg[i] or 'dis' in msg[i]:
        #         dis_ = str(msg[i]).strip().split(':')[1]
        #         if len(dis_) > 0 and is_number(dis_):
        #             try:
        #                 if int(dis_) > 0:
        #                         dis = int(dis_)
        #                         f1 = 1
        #                         log += f'折扣修改为 {dis} '
        #                 else:
        #                         await xg.finish("修改商品的折扣要大于0！", at_sender=True) 
        #             except ValueError as e:
        #                 await xg.finish("[dis]你的奇怪数字是什么！请重新输入！！", at_sender=True)
        #     elif '上架限时' in msg[i] or 'lim' in msg[i]:
        #         add_lim_ = str(msg[i]).strip().split(':')[1]
        #         if len(add_lim_) > 0 and is_number(add_lim_):
        #             try:
        #                 if add_lim_ > 0:
        #                         add_lim = add_lim_
        #                         f1 = 1
        #                         log += f'上架限时修改为 {add_lim} '
        #                 else:
        #                         await xg.finish("修改商品的上架限时要大于0！", at_sender=True) 
        #             except ValueError as e:
        #                 await xg.finish("[lim]你的奇怪数字是什么！请重新输入！！", at_sender=True)
        #     elif '折扣限时' in msg[i] or 'dislim' in msg[i]:
        #         dis_lim_ = str(msg[i]).strip().split(':')[1]
        #         if len(dis_lim_ ) > 0 and is_number(dis_lim_ ):
        #             try:
        #                 if dis_lim_  > 0:
        #                         dis_lim = dis_lim_ 
        #                         f1 = 1
        #                         log += f'折扣限时修改为 {dis_lim} '
        #                 else:
        #                         await xg.finish("修改商品的折扣限时要大于0！", at_sender=True) 
        #             except ValueError as e:
        #                 await xg.finish("[dis_lim]你的奇怪数字是什么！请重新输入！！", at_sender=True)
        #     elif '每日购买' in msg[i] or 'daylim' in msg[i]:
        #         day_lim_ = str(msg[i]).strip().split(':')[1]
        #         if len(day_lim_ ) > 0 and is_number(day_lim_ ):
        #             try:
        #                 if int(day_lim_ ) > 0:
        #                         day_lim = int(day_lim_ )
        #                         f1 = 1
        #                         log += f'每日购买限制修改为 {day_lim} '
        #                 else:
        #                         await xg.finish("修改商品的每日购买限制要大于0！", at_sender=True) 
        #             except ValueError as e:
        #                 await xg.finish("[day_lim]你的奇怪数字是什么！请重新输入！！", at_sender=True)
        #     elif '购买条件' in msg[i] or 'lim' in msg[i]:
        #         lim_ = str(msg[i]).strip().split(':')[1]
        #         if len(day_lim_ ) > 0 and is_number(day_lim_ ):
        #             try:
        #                 if int(day_lim_ ) > 0:
        #                         day_lim = int(day_lim_ )
        #                         f1 = 1
        #                         log += f'购买条件修改为 {msg[i]} '
        #                 else:
        #                         await xg.finish("修改商品的每日购买限制要大于0！", at_sender=True) 
        #             except ValueError as e:
        #                 await xg.finish("[day_lim]你的奇怪数字是什么！请重新输入！！", at_sender=True)
        goods = await goods_info(arg,0,price,des,lim,dis,dis_lim,add_lim,day_lim,add = False)
        goods_in = {}
        if  goods != None:
            goods_in = goods
        price = goods_in['price']
        des = goods_in['des']
        lim = goods_in['lim']
        dis= goods_in['dis']
        dis_lim = goods_in['dis_lim']
        add_lim = goods_in['add_lim']
        day_lim = goods_in['day_lim']
        log = goods_in['log']
        if isinstance(goods,dict):
                if await PersonalGoods.add_goods_now(uid,group,msg[0],0,price,des,lim,dis,dis_lim,add_lim,day_lim) :
                        await xg.finish(f'已将 {msg[0]} 的{log}成功！')
                else :
                    await xg.finish(f"该商品 {msg[0]} 已经清空，无法修改信息啦")
        elif isinstance(goods,str):
            await xg.finish(f'{goods}',at_sender=True)

@scheduler.scheduled_job(
    "interval",
    seconds=30,
)
async def _():
    bot = get_bot()
    time = datetime.now()
    y_m_d,h_m = time_add(time,0)
    y_m_d_h_m = y_m_d+h_m
    y,mon,d,h,m = fen(y_m_d_h_m)
    gl = await bot.get_group_list()
    gl = [g["group_id"] for g in gl]
    for g in gl:
        good_lst,owner = await PersonalGoods.get_group_goods(g)
        for i in good_lst:
            add_limit_time = good_lst[i]['add_limit_time']
            if add_limit_time != '0' :
                ay,amou,ad,ah,am = fen(add_limit_time)
                if y < ay:
                    continue
                elif y == ay:
                    if mon < amou:
                        continue
                    elif mon == amou:
                        if d < ad:
                            continue
                        elif d == ad:
                            if h < ah:
                                continue
                            elif h ==ah:
                                if m <= am:
                                    continue
                num = good_lst[i]['num']
                if await PersonalGoods.change_goods_now(owner,g,i,num) :
                                for _ in range(num):
                                    await BagUser.add_property(owner,g,i)
                                logger.info(f'拥有者 {owner} 在群 {g} 的限时商品{i} 已下架')


@scheduler.scheduled_job(
    "interval",
    seconds=30,
)
async def _():
    bot = get_bot()
    time = datetime.now()
    y_m_d,h_m = time_add(time,0)
    y_m_d_h_m = y_m_d+h_m
    y,mon,d,h,m = fen(y_m_d_h_m)
    result_set = {}
    gl = await bot.get_group_list()
    gl = [g["group_id"] for g in gl]
    for g in gl:
        good_lst,owner = await PersonalGoods.get_group_goods(g)
        result_set[g] = {}
        result_set[g][owner] = ''
        for i in good_lst:
            price = good_lst[i]['price']
            des = good_lst[i]['description']
            dis = good_lst[i]['discount']
            lim = good_lst[i]['limit']
            dis_lim = good_lst[i]['discount_limit_time']
            add_lim = good_lst[i]['add_limit_time']
            day_lim = good_lst[i]['daily_limit']
            if dis_lim != '0' :
                ay,amou,ad,ah,am = fen(dis_lim)
                if y < ay:
                    continue
                elif y == ay:
                    if mon < amou:
                        continue
                    elif mon == amou:
                        if d < ad:
                            continue
                        elif d == ad:
                            if h < ah:
                                continue
                            elif h ==ah:
                                if m <= am:
                                    continue
                if await PersonalGoods.add_goods_now(owner,g,i,0,price,des,lim,1,'0',add_lim,day_lim) :
                    if result_set[g][owner] == '':
                        result_set[g][owner] = f'{i}-'
                    else:
                        re = result_set[g][owner]
                        re += f'{i}-'
                        result_set[g][owner] = re
    for g in result_set:
        good_lst,owner = await PersonalGoods.get_group_goods(g)
        if result_set[g][owner] != '':
            for n in result_set[g]:
                name = await GroupInfoUser.get_group_member_nickname(n, g)
                result = f'商户 {name} 的折扣商品\n'
                owner_goods = result_set[g][n]
                owner_goods = owner_goods.split('-')
                for j in owner_goods :
                    result += f'{j}\n'
                result += '已恢复原价'
                try:
                    await bot.send_group_msg(group_id=g, message=result)
                except ActionFailed:
                    logger.warning(f"{g} 群被禁言中，无法发送限时商品还原情况")


