from services.db_context import db
from typing import List
from services.log import logger



class PersonalGoods(db.Model):
    __tablename__ = "personal_goods"
    id = db.Column(db.Integer(), primary_key=True)
    owner_qq = db.Column(db.BigInteger(),nullable=False) #拥有者
    group_id = db.Column(db.BigInteger(),nullable=False)#群号
    goods_num = db.Column(db.Integer(), nullable=False) #数量
    goods_name = db.Column(db.TEXT(), nullable=False)  # 名称
    goods_price = db.Column(db.Integer(), nullable=False)  # 价格
    property = db.Column(db.JSON(), nullable=False, default={})  # 新道具字段

    _idx1 = db.Index("personalgoods_group_users_idx1", "owner_qq","group_id","goods_name", unique=True)

    @classmethod
    async def add_goods(
        cls,
        owner:int,
        group_id:int,
        goods_name: str,
        num:int,
        goods_price: int,) -> bool:
        """
        说明：
            上架商品
        参数：
            :param goods_name: 商品名称
            :param goods_num: 商品数量
            :param goods_price: 商品价格
        """
        try:
            if not await cls.get_goods_info(owner_qq = owner,goods_name = goods_name):
                await cls.create(
                    owner_qq = owner,
                    group_id = group_id,
                    goods_name=goods_name,
                    goods_num=num,
                    goods_price=goods_price,
                )
                return True
            else :
                query = (
                await cls.query.where((cls.goods_name == goods_name) & (cls.owner_qq == owner))
                .with_for_update()
                .gino.first()
            )
            if not query:
                return False
            gn = query.goods_num
            gn += num
            await query.update(
                goods_price=goods_price or query.goods_price,
                goods_num = gn or query.goods_num,
            ).apply()
            return True

        except Exception as e:
            logger.error(f" PersonalGoods add_goods 发生错误 {type(e)}：{e}")
        return False


    @classmethod
    async def change_goods(cls,owner:int,group_id:int, goods_name: str,change_num:int) -> bool:
        """
        说明：
            下架商品
        参数：
            :param goods_name: 商品名称
            :param goods_num: 商品数量
        """
        try:
            query = (
                await cls.query.where((cls.goods_name == goods_name) & (cls.owner_qq == owner) & (cls.group_id == group_id))
                .with_for_update()
                .gino.first()
            )
            if not query:
                return False
            gn = query.goods_num
            if gn == 0 :
                return False
            else:
                gn -= change_num
                await query.update(
                    goods_num = gn ,
                ).apply()
                return True
        except Exception as e:
            logger.error(f"PersonalGoods change_goods 发生错误 {type(e)}：{e}")
        return False

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
        query = await cls.query.where((cls.owner_qq == owner_qq) & (cls.group_id == group_id)).with_for_update().gino.all()
        #id_lst = [x.id for x in query]
        goods_lst = [x if x.owner_qq == owner_qq and x.group_id == group_id else x.owner_qq  for x in query]
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
        num:int,) -> bool:

        for _ in range(num):
            query = cls.query.where((cls.owner_qq == owner) & (cls.group_id == group_id))
            query = query.with_for_update()
            user = await query.gino.first()
            if user:
                            p = user.property
                            if p.get(goods_name) is None:
                                p[goods_name] = 1
                            else:
                                p[goods_name] += 1
                            await user.update(property=p).apply()
            else:
                            await cls.create(owner_qq = owner, group_id=group_id, property={goods_name: 1})


func_text = PersonalGoods()