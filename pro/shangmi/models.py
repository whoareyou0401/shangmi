# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models

from django.contrib.postgres.fields import ArrayField

import choices
# Create your models here.


class User(models.Model):
    openid = models.CharField(
        verbose_name=u'用户ID',
        db_index=True,
        max_length=100,
        unique=True)
    add_time = models.DateTimeField(
        verbose_name=u'生成日期',
        auto_now_add=True)
    wx_name = models.CharField(
        verbose_name=u'昵称',
        db_index=True,
        max_length=128,
        blank=True,
        null=True)
    name = models.CharField(
        verbose_name=u'姓名',
        db_index=True,
        max_length=128,
        blank=True,
        null=True)
    icon = models.CharField(
        verbose_name=u'头像',
        db_index=True,
        max_length=512,
        blank=True,
        null=True)
    phone = models.CharField(
        verbose_name=u'手机号',
        max_length=23,
        null=True,
        blank=True)
    source = models.CharField(
        verbose_name=u'用户来源',
        max_length=56,
        null=True,
        blank=True)
    is_new = models.BooleanField(
        verbose_name=u'是否是新用户',
        default=True)
    update_time = models.DateTimeField(
        verbose_name=u'注册时间',
        null=True)


class Saler(models.Model):
    user = models.OneToOneField(
        User,
        verbose_name=u'店员',
        db_index=True,
        null=True,
        blank=True)
    name = models.CharField(
        verbose_name=u'姓名',
        db_index=True,
        max_length=128,
        blank=True,
        null=True)
    phone = models.CharField(
        verbose_name=u'手机号',
        max_length=23,
        null=True,
        blank=True)
    is_new = models.BooleanField(
        verbose_name=u'是否是新用户',
        default=True)
    update_time = models.DateTimeField(
        verbose_name=u'修改状态时间',
        auto_now_add=True,
        null=True,
        blank=True)
    status = models.IntegerField(
        verbose_name=u'店员状态',
        choices=choices.SALER_STATUS)
    is_boss = models.BooleanField(
        verbose_name=u'是否是店长',
        default=False)


class Store(models.Model):
    store_name = models.CharField(
        verbose_name=u'门店名称',
        max_length=128)
    store_address = models.CharField(
        verbose_name=u'门店地址',
        max_length=256,
        null=True,
        blank=True)
    lat = models.FloatField(
        verbose_name=u'纬度',
        null=True,
        blank=True)
    lng = models.FloatField(
        verbose_name=u'经度',
        null=True,
        blank=True)
    boss = models.OneToOneField(
        User,
        verbose_name=u'店长',
        db_index=True,
        null=True,
        blank=True)
    boss_name = models.CharField(
        verbose_name=u'店老板名字',
        max_length=32,
        null=True,
        blank=True)
    phone = models.CharField(
        verbose_name=u'电话',
        max_length=15,
        null=True,
        blank=True)
    status = models.BooleanField(
        verbose_name=u'激活状态',
        default=False)
    add_time = models.DateTimeField(
        verbose_name=u'生成日期',
        auto_now_add=True,
        null=True)


class StoreSalerMap(models.Model):
    saler = models.ForeignKey(
        Saler,
        verbose_name=u'店员',
        null=True,
        blank=True)
    store = models.ForeignKey(
        Store,
        verbose_name=u'门店',
        null=True,
        blank=True)



class Active(models.Model):
    name = models.CharField(
        verbose_name=u'活动名称',
        max_length=58,
        db_index=True)
    add_time = models.DateTimeField(
        verbose_name=u'生成日期',
        auto_now_add=True)
    send_phone_url = models.CharField(
        verbose_name=u'获取验证码的链接',
        max_length=512,
        null=True,
        blank=True)
    send_phone_params = ArrayField(
        models.CharField(
            max_length=256,
            null=True),
        verbose_name=u'参数名',
        null=True)
    send_code_url = models.CharField(
        verbose_name=u'提交验证码手机号链接',
        max_length=128,
        null=True,
        blank=True)
    send_code_params = ArrayField(
        models.CharField(
            max_length=256,
            null=True),
        verbose_name=u'参数名',
        null=True) 
    status = models.IntegerField(
        verbose_name=u'活动状态',
        choices=choices.ACTIVE_STATUS)


class ActiveAcountConf(models.Model):
    active = models.OneToOneField(
        Active,
        verbose_name=u'活动',
        db_index=True)
    text = models.CharField(
        verbose_name=u'提示语',
        max_length=256,
        null=True,
        blank=True)
    acount_time = models.DateField(
        verbose_name=u'提现日期',
        null=True,
        blank=True)


class ActiveStoreMap(models.Model):
    store = models.ForeignKey(
        Store,
        verbose_name=u'门店',
        db_index=True)
    active = models.ForeignKey(
        Active,
        verbose_name=u'活动',
        db_index=True)


class CustomerGetPriceLog(models.Model):
    customer = models.ForeignKey(
        User,
        verbose_name=u'消费者',
        db_index=True)
    price = models.FloatField(
        verbose_name=u'获得的随机金额')
    active = models.ForeignKey(
        Active,
        verbose_name=u'消费者参加的活动',
        db_index=True)
    store = models.ForeignKey(
        Store,
        verbose_name=u'活动对应的门店',
        db_index=True)
    is_writeoff = models.BooleanField(
        verbose_name=u'是否已经核销',
        default=False)
    add_time = models.DateTimeField(
        verbose_name=u'生成日期',
        auto_now_add=True)
    update_time = models.DateTimeField(
        verbose_name=u'更新日期日期',
        null=True,
        blank=True)
    class Meta:
        unique_together=("customer", "active", "store")


class ActiveLog(models.Model):
    active_map = models.ForeignKey(
        ActiveStoreMap,
        verbose_name=u'活动',
        db_index=True)
    saler = models.ForeignKey(
        Saler,
        verbose_name=u'店员',
        null=True,
        blank=True)
    customer = models.ForeignKey(
        User,
        verbose_name=u'消费者',
        null=True)
    time = models.DateTimeField(
        verbose_name=u'生成日期',
        auto_now_add=True)
    customer_get_price_log = models.ForeignKey(
        CustomerGetPriceLog,
        verbose_name=u'对应生产的log id',
        null=True,
        blank=True)
    is_writeoff = models.BooleanField(
        verbose_name=u'是否已经结算',
        default=False)


class ActiveImages(models.Model):
    active = models.ForeignKey(
        Active,
        verbose_name=u'活动',
        db_index=True)
    images = ArrayField(
        models.CharField(
            max_length=256,
            null=True),
        verbose_name=u'图片名称',
        null=True)
    icon = models.CharField(
        verbose_name=u'注册页图片',
        max_length=256,
        null=True,
        blank=True)


class ActiveRandomRange(models.Model):
    active = models.ForeignKey(
        Active,
        verbose_name=u'活动ID',
        db_index=True)
    random_start = models.FloatField(
        verbose_name=u'随机起始金额')
    random_end = models.FloatField(
        verbose_name=u'随机结束金额')


class AdjustAccounts(models.Model):
    adminor = models.ForeignKey(
        User,
        verbose_name=u'操作人',
        db_index=True)
    store = models.ForeignKey(
        Store,
        verbose_name=u'门店',
        db_index=True)
    active = models.ForeignKey(
        Active,
        verbose_name=u'对应的活动',
        db_index=True)
    price = models.FloatField(
        verbose_name=u'结算金额')
    time = models.DateTimeField(
        verbose_name=u'结算时间',
        auto_now_add=True)
    # log = models.ForeignKey(
    #     ActiveLog,
    #     verbose_name=u'对应的log')


class StoreMoneyDistribution(models.Model):
    active = models.OneToOneField(
        Active,
        verbose_name=u'活动',
        db_index=True)
    saler_money = models.FloatField(
        verbose_name=u'店员给予的分成',
        default=0)
    boss_money = models.FloatField(
        verbose_name=u'店长直接核销的奖励金额',
        default=0)
    boss_distribute_money = models.FloatField(
        verbose_name=u'店员核销对应的店长提成',
        default=0)


class UserConfirmPhone(models.Model):
    phone = models.CharField(
        verbose_name=u'手机号',
        max_length=15,
        db_index=True,
        primary_key=True)
    get_phone_time = models.DateTimeField(
        verbose_name=u'获得手机号时间',
        auto_now_add=True)
    is_used = models.BooleanField(
        verbose_name=u'是否被使用了',
        default=False)
    used_time = models.DateTimeField(
        verbose_name=u'领取奖励的时间',
        null=True,
        blank=True)
    active = models.ForeignKey(
        Active,
        verbose_name=u'活动',
        db_index=True,
        null=True,
        blank=True)