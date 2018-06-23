#-*- coding:utf-8 -*-
from __future__ import absolute_import

import logging
from celery import task,shared_task
from celery.utils.log import get_task_logger
from celery.schedules import crontab
import requests
import json
import sys
import datetime
# logger = get_task_logger(__name__)
logger = logging.getLogger('simple_example')
formatter = logging.Formatter('%(asctime)s %(levelname)-8s: %(message)s')
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler("test.log")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

TEMPLATE_ID="AK1JyDrBj1awj2CIvZrH_Iow6yrT1tYJO-yd-6D8cB0"
APPID = "wx7183d4969917ae3b"
SECRET = "7693993d21886417790869a9f6619660"

def get_access_token_function(appid, secret):
    response = requests.get(
            url="https://api.weixin.qq.com/cgi-bin/token",
            params={
                "grant_type": "client_credential",
                "appid": appid,
                "secret": secret,
            }
        )
    response_json = response.json()
    access_token = response_json['access_token']
    return access_token


def send_template_msg(template_id, touser, token):
    template_data = {
           "touser":touser,
           "template_id":template_id,
           "miniprogram":{
             "appid":"wx11efe16cfc4b1a70",
             "pagepath":"pages/shelf/shelf"
           },
           # "url":'https://b.ichaomeng.com',
           # "topcolor": 'red',
           "data":{
               "first": {
                'value': "不再为明天吃什么发愁，来看看明天的午餐吧",
                'color': '#CC6633'
               },
               "storeName":{
                'value': "轻盈厨房"
               },
               "bookTime": {
                'value': "至23:00"
               },
               "orderId": {
                'value': "点击预定",
                'color': "#9933FF"
               },
               "orderType": {
                'value': "预定明天午餐"
               },
               "remark": {
                'value': "每天有特惠商品哦~"
               }
           }
       }
    url='https://api.weixin.qq.com/cgi-bin/message/template/send?access_token=%s' % token
    response = requests.post(url, data=json.dumps(template_data))
    response_json = response.json()
    errcode = response_json.get('errcode')
    errmsg = response_json.get('errmsg')
    if (errcode == 0 and errmsg==u'ok'):
        return {'data': response_json.get('msgid')}
    else:
        return {'data': 'errmsg'}

def get_all_users(access_token):
    url = "https://api.weixin.qq.com/cgi-bin/user/get?access_token=" +  access_token
    response = requests.get(url)
    response_json = response.json()
    return response_json.get('data').get('openid')



@shared_task
def subscribe_rice():
    access_token = get_access_token_function(APPID, SECRET)
    users = get_all_users(access_token)
    for u in users:
        send_template_msg(TEMPLATE_ID, u, access_token)
subscribe_rice()
# @shared_task
# def subscribe_test():
#     logger.info('this is information')