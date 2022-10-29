from services.db_context import db
from typing import List, Tuple
from services.log import logger
from typing import Dict
import datetime



class PersonalGoods(db.Model):
    __tablename__ = "personal_goods"
    id = db.Column(db.Integer(), primary_key=True)
    owner_qq = db.Column(db.BigInteger(),nullable=False) #拥有者
    group_id = db.Column(db.BigInteger(),nullable=False)#群号
    property = db.Column(db.JSON(), nullable=False, default={})  # 新道具字段

    _idx1 = db.Index("personalgoods_group_users_idx1", "owner_qq","group_id", unique=True)


    @classmethod
    async def get_goods_info(cls, owner_qq: int, goods_name: str) -> "PersonalGoods":
        """
        说明：
            获取商品对象
        参数：
            :param goods_name: 商品名称
        """
        return await cls.query.where((cls.goods_name == goods_name) & (cls.owner_qq == owner_qq) ).gino.first()

    @classmethod
    async def get_all_goods(cls,owner_qq:int,group_id:int) -> List["PersonalGoods"]:
        """
        说明：
            获得全部有序商品对象
        """
        query = await cls.query.gino.all()
        id_lst = [x.id for x in query]
        goods_lst = []
        for _ in range(len(query)):
            min_id = min(id_lst)
            goods_lst.append([x for x in query if x.id == min_id][0])
            id_lst.remove(min_id)
        return goods_lst

    @classmethod
    async def update_goods(
        cls,
        owner_qq:int,
        group_id:int,
        goods_name: str,
        goods_price:int,
    ) -> bool:
        """
        说明：
            更新商品信息
        参数：
            :param goods_name: 商品名称
            :param goods_price: 商品价格
        """
        try:
            query = (
                await cls.query.where((cls.goods_name == goods_name) & (cls.owner_qq == owner_qq) & (cls.group_id == group_id))
                .with_for_update()
                .gino.first()
            )
            if not query:
                return False
            gn = query.goods_num
            if gn == 0 :
                return False
            await query.update(
                goods_price=goods_price or query.goods_price,
            ).apply()
            return True
        except Exception as e:
            logger.error(f"PersonalGoods update_goods 发生错误 {type(e)}：{e}")
        return False

    @classmethod
    async def get_owner_qq(cls,goods_name:str, owner: int,group_id:int,) -> "PersonalGoods":
        """
        说明：
            获取拥有者
        参数：
            :param owner_qq: 拥有者qq号
        """
        return await cls.query.where((cls.goods_name == goods_name) & (cls.owner_qq == owner) & (cls.group_id == group_id)).gino.first()

    @classmethod
    async def add_goods_now(cls,
        owner:int,
        group_id:int,
        goods_name: str,
        num:int,
        price:int,
        description: str = '无',
        limit :dict = {},
        discount: float = 1,
        discount_limit_time: str = '0',
        add_limit_time: str = '0',
        daily_limit: int = 0,) -> bool:
            """
            说明：
                (数据库)上架/更改商品
            参数：
                :param owner: 拥有者qq号
                :param group_id: 群号
                :param goods_name: 商品名称
                :param num: 上架数量
                :param price: 商品价格
                :param add_time: 上架时间
                :param description: 商品描述
                :param limit: 购买该商品条件
                :param discount: 商品折扣
                :param discount_limit_time: 商品折扣限时
                :param add_limit_time: 商品上架限时
                :param daily_limit: 每日购买限制
            """
            query = cls.query.where((cls.owner_qq == owner) & (cls.group_id == group_id))
            query = query.with_for_update()
            user = await query.gino.first()
            if user:
                            p = user.property
                            if p.get(goods_name) is None:
                                p[goods_name] = {'num':num,'price':price,'description':description,'discount':discount,'discount_limit_time':discount_limit_time,'add_limit_time':add_limit_time,'daily_limit':daily_limit,'limit':limit}
                            else:
                                num_l = p[goods_name]['num']
                                num_l += num
                                p[goods_name] = {'num':num_l,'price':price,'description':description,'discount':discount,'discount_limit_time':discount_limit_time,'add_limit_time':add_limit_time,'daily_limit':daily_limit,'limit':limit}
                            await user.update(property=p).apply()
                            return True
            else:
                            await cls.create(owner_qq = owner, group_id=group_id, property={goods_name: {'num':num,'price':price,'description':description,'discount':discount,'discount_limit_time':discount_limit_time,'add_limit_time':add_limit_time,'daily_limit':daily_limit,'limit':limit}})
                            return True
    

    @classmethod
    async def get_goods(cls,owner_qq:int,group_id:int) :
        """
        说明：
            获取用户的全部有序商品信息
        参数：
            :param owner_qq: 拥有者qq号
            :param group_id: 群号
        """
        query = cls.query.where((cls.owner_qq == owner_qq) & (cls.group_id == group_id))
        user = await query.gino.first()
        if user:
            return user.property
        else:
            await cls.create(
                owner_qq = owner_qq,
                group_id = group_id,
            )
            return {}

    @classmethod
    async def change_goods_now(cls,owner:int,group_id:int, goods_name: str,change_num:int = 1) -> bool:
        """
        说明：
            下架商品
        参数：
            :param owner: 拥有者qq号
            :param group_id: 群号
            :param goods_name: 商品名称
            :param goods_num: 商品数量
        """
        query = cls.query.where((cls.owner_qq == owner) & (cls.group_id == group_id))
        query = query.with_for_update()
        user = await query.gino.first()
        if user:
            property_ = user.property
            if goods_name in property_:
                if property_[goods_name]['num'] == change_num:
                    del property_[goods_name]
                else:
                    description = property_[goods_name]['description']
                    discount = property_[goods_name]['discount']
                    limit = property_[goods_name]['limit']
                    discount_limit_time = property_[goods_name]['discount_limit_time']
                    add_limit_time = property_[goods_name]['add_limit_time']
                    daily_limit = property_[goods_name]['daily_limit']
                    num_l = property_[goods_name]['num']
                    num_l -= change_num
                    price = property_[goods_name]['price']
                    property_[goods_name] = {'num':num_l,'price':price,'description':description,'discount':discount,'discount_limit_time':discount_limit_time,'add_limit_time':add_limit_time,'daily_limit':daily_limit,'limit':limit}
                await user.update(property=property_).apply()
                return True
        return False


    @classmethod
    async def get_goods_addtime(cls,owner_qq:int,group_id:int) :
        """
        说明：
            获取该商品上架时间
        参数：
            :param owner_qq: 拥有者qq号
            :param group_id: 群号
            :param goods_name: 商品名称
        """
        query =  cls.query.where((cls.owner_qq == owner_qq) & (cls.group_id == group_id))
        user = await query.gino.first()
        goods_lst = {}
        for i in user.property:
            goods_name = i
            addtime = user.addtime
            goods_lst[goods_name] = addtime

        return goods_lst

    @classmethod
    async def get_group_goods(cls,group_id:int) -> Tuple[dict,int]:
        """
        说明：
            获取群全部有序商品信息
        参数：
            :param group_id: 群号
        """
        query = cls.query.where((cls.group_id == group_id))
        user = await query.gino.first()
        if user:
            return user.property,user.owner_qq
        else:
            await cls.create(
                group_id = group_id,
            )
            return {},0    


func_text = PersonalGoods()

