# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render
from django.http import HttpResponse, QueryDict
from django.views.generic.base import View
from models import *
from decorators import standard_api, token_required
from django.utils.decorators import method_decorator
import utils
import datetime
from django.utils import timezone
from django.conf import settings
from django.forms.models import model_to_dict
from django.core.cache import cache
import requests
import json
import pandas
import random
from sqlalchemy import text
import sqlalchemy
from django.db import connection
import re
import getqr
# import uuid
# import boto
# import StringIO
# import oss2
# import base64,hashlib
endpoint = 'http://oss-cn-shanghai.aliyuncs.com'
access_key_id = 'LTAIXPTosazV9jSq'
access_key_secret = '7uXYe15rjLzEjStAwVraExvAWFkxIw'
bucket_name = 'share-msg'
# Create your views here.
BUSSINESS_DB_URL='postgres://vshare:vshare!2017@139.129.227.138:5432/vsharedb'
data_engine = sqlalchemy.create_engine(BUSSINESS_DB_URL)
area_zips = ['100000', '200000', '518000', '510000']

def tt(request):
    return HttpResponse('bde10ed98224c307ea1141708130629b')


def token(request):
    params = request.GET
    code = params.get('code')
    avatar = params.get('avatar')
    gender = params.get('gender')
    nick_name = params.get('name')
    mini_type = params.get('mini_type')
    if mini_type == 'background':
        appid = 'wx4a8c99d5d8b43556'
        secret = '014ad578b31357e53b61b9ab69db0761'
    elif mini_type == 'customer':
        appid = 'wx8b50ab8fa813a49e'
        secret = 'b32f63c36ea123710173c4c9d4b15e8b'
    else:
        appid = 'wxebd828458f8b2b38'
        secret = 'a40cb9c5ecb1f4f5c0f31b75829fed03'
    url = settings.SMALL_WEIXIN_OPENID_URL
    params = {"appid": appid,
              "secret": secret,
              "js_code": code,
              "grant_type": 'authorization_code'
            }
    response = requests.get(url, params=params)
    data = json.loads(response.content)
    if 'openid' in data:
        openid= data.get('openid')	
        token = utils.generate_validate_token(openid)
        user = User.objects.get_or_create(openid=openid)[0]
        user.wx_name = nick_name
        user.icon = avatar
        user.source = mini_type
        user.save()
        return HttpResponse(json.dumps({'code':0, 'data':{'token': token}}),
                                             content_type = 'application/json')
    else:
        return HttpResponse(json.dumps({'code':1, 'msg':'failed'}),
                                             content_type = 'application/json')


@method_decorator([standard_api(methods=('GET', ))], name='dispatch')
class CodeAPI(View):
    def get(self, request):
        params = request.GET
        active_id = int(params.get('active_id'))
        phone = params.get('phone')
        user = utils.request_user(request)
        if active_id == 1:
            try:
                area = utils.get_phone_area(phone)
                area_zip = area['zip']
                if area_zip not in area_zips:
                    return {'code': 2, 'msg': u'该号码归属地不能参与'}
            except:
                pass
            url = 'https://mcp.ddky.com/weixin/rest.htm'
            date = datetime.datetime.now()
            date = str(date).split('.')[0]
            request_data = {
                'plat':'H5',
                'platform':'H5',
                't': date,
                'v':'1.0',
                'versionName':'3.5.0',
                'phone': phone,
                'method':'ddky.promotion.onebuy.sendcode',
            }
            end_url = utils.get_url(url, request_data)
            response = requests.get(end_url)
            res = json.loads(response.content)
            return res
        if active_id == 2:
            url = "https://m.ierfa.cn/regist/appSendMessage"
            request_data = {
                'mobileNum': phone,
                'codeType': 'regist'}
            response = requests.get(url, params=request_data)
            cookies = response.cookies.get_dict()
            cache.set(user.id, cookies, 60*60)
            res = json.loads(response.content)
            if int(res.get('status')) == 1 and res.get('data').get('code') == '1':
                return {'code':0 ,'msg': {'newToken': res.get('data').get('newToken')}}
            if int(res.get('status')) == 1 and res.get('data').get('code') == '0':
                return {'code':1 ,'msg': u'您已注册,无法参与'}
            else:
                return {'code':1 ,'msg': u'发送失败'}


@method_decorator([standard_api(methods=('GET', 'POST'))], name='dispatch')
class CodePhoneAPI(View):
    def post(self, request):
        params = QueryDict(request.body)
        active_id = int(params.get('active_id'))
        phone = params.get('phone')
        code = params.get('code')
        user = utils.request_user(request)
        if active_id == 1:
            vcId = 12808
            skuId = '50034222'
            try:
                actives_map = utils.get_actives()
                actives = actives_map.get('result').get('pmList')
                if actives_map.get('code') == 0:
                    for active in actives:
                        if active.get('isOn') == 1:
                            vcId = active.get('id')
                            skuId = active.get('skuId')
                            break
            except Exception as e:
            	return {'code': 2, 'data': u'今天结束啦，明天再来'}
            try:
                area = utils.get_phone_area(phone)
                area_zip = area['zip']
                if area_zip not in area_zips:
                    return {'code': 2, 'msg': u'该号码归属地不能参与'}
            except:
                pass
            url = 'https://mcp.ddky.com/weixin/rest.htm'
            date = datetime.datetime.now()
            date = str(date).split('.')[0]
            # source_id = random.randint(1, 10)
            # source = '2m_lyj_shijie%s' % (str(source_id))
            source = '2m_lyj_shijie10'
            request_data = {
                'activityId':587,
                'channel': source,
                'city':'beijing',
                'lat':39.91488908,
                'lng':116.40387397,
                'method':'ddky.promotion.onebuy.new.activity.receivecoupon',
                'phone':phone,
                'plat':'H5',
                'platform':'H5',
                'shopId':'100012',
                'skuId':str(skuId),
                'smsCode': code,
                't': date,
                'v':'1.0',
                'vcId':int(vcId),
                'versionName':'3.5.0'
            }
            end_url = utils.get_url(url, request_data)
            response = requests.get(end_url)
            try:
            	json_str = re.findall(r'[^()]+', response.content)[1]
            	res = json.loads(json_str)
            except Exception as e:
            	res = json.loads(response.content)
                print res
            
            if (res.get('code') == 0 or res.get('code') == '0'):
                user.is_new = False
            user.phone = phone
            user.update_time = timezone.now()
            user.save()
            return res

        elif active_id == 2:
            today = timezone.now()
            year = today.year
            month = today.month
            day = today.day
            today_count = ActiveLog.objects.filter(time__year=year,
                                          time__month=month,
                                          time__day=day, 
                                          active_map=19).count()
            if today_count >= 300:
                return {'code': 3,'data': u'今日名额已满'}
            pwd = params.get('pwd')
            cookies = cache.get(user.id)
            token_url = "https://m.ierfa.cn/login/token"
            token_response = requests.get(token_url, cookies=cookies)
            
            res = json.loads(token_response.content)
            if int(res.get('status')) == 1:
                reg_token = res.get('token')
                regist_url = "https://m.ierfa.cn/regist/appSMSSave"
                regist_data = {
                    'source':65,
                    'mobileNum': phone,
                    'token': reg_token,
                    'activeCode': code,
                    'logpassword': pwd
                }
                user.phone = phone
                user.update_time = timezone.now()
                user.save()
                regist_response = requests.get(regist_url, params=regist_data, cookies=cookies)
                regist_res = json.loads(regist_response.content)
                if int(regist_res.get('status')) == 1:
                    return {'code': 0, 'data': 'ok'}
                else:
                    return {'code': 2, 'data': regist_res.get('msg')}
            else:
                return {'code': 2, 'data': '请求失败'}


@method_decorator([standard_api(methods=('GET', 'POST'))], name='dispatch')
class StoreAPI(View):
    def get(self, request):
    	params = request.GET
        print params
    	if 'store_id' in params:
    		store_id = int(params.get('store_id'))
    		store = Store.objects.get(id=store_id)
    		return {'code': 0, 'data': model_to_dict(store)}
    	else:
	    	stores = Store.objects.all()
	    	res = []
	    	for store in stores:
	    		res.append(model_to_dict(store))
	    	return {'code': 0, 'data': res}

    def post(self, request):
    	user = utils.request_user(request)
    	params = QueryDict(request.body)
    	store_name = params.get('store_name')
    	address = params.get('store_address')
    	lat = params.get('lat')
    	lng = params.get('lng')
    	phone = params.get('phone')
    	boss_name = params.get('boss_name')
    	store = Store.objects.get_or_create(
    		store_name=store_name,
    		store_address=address,
    		lat=float(lat),
    		lng=float(lng),
    		boss_name=boss_name,
    		phone=phone)[0]
    	store.save()
    	actives = Active.objects.filter(status=1)
    	for active in actives:
    		amap = ActiveStoreMap.objects.get_or_create(
    			store=store,
    			active=active)[0]
    		amap.save()
    	return {'code': 0, 'data': 'ok'}


@method_decorator([standard_api(methods=('GET', 'POST'))], name='dispatch')
class StoreSearchAPI(View):
    def get(self, request):
    	params = request.GET
    	key_word = params.get('key_word')
    	stores = Store.objects.filter(
    		store_name__contains=key_word)
    	res = []
    	for store in stores:
    		res.append(model_to_dict(store))
    	return {'code': 0, 'data': res}


@method_decorator([standard_api(methods=('GET', 'POST'))], name='dispatch')
class ActiveAPI(View):
    def get(self, request):
        params = request.GET
        store_id = int(params.get('store_id'))
        sql = """
            SELECT 
                active.id,
                active.name
            FROM 
                shangmi_activestoremap AS ssmap
            LEFT JOIN
                shangmi_active AS active
            ON 
                ssmap.active_id=active.id
            WHERE 
                ssmap.store_id={store_id}
            ORDER BY 
                active.add_time DESC
        """.format(store_id=store_id)
        cur = connection.cursor()
        cur.execute(sql)
        active_list = utils.dictfetchall(cur)
        return {'code': 0, 'data': active_list}


@method_decorator([standard_api(methods=('GET', 'POST'))], name='dispatch')
class StoreActiveverviewAPI(View):
	def get(self, request):
		params = request.GET
		store_id = int(params.get('store_id'))
		data_type = params.get('data_type')
		active_num = ActiveStoreMap.objects.filter(
			store_id=store_id, 
			active__status=1).count()
		res = []
		item_detail_list = utils.get_store_active_log(store_id, data_type)
		active_money_map = {}
		for item in item_detail_list:
			active_id = item['active_id']
			distribute = StoreMoneyDistribution.objects.get(active_id=active_id)
			person_count = count = 0
			if item.get('is_boss') == True:
				distribute = distribute.boss_money 
			else:
				distribute = distribute.boss_distribute_money

			if active_id in active_money_map:
				before_amount = active_money_map[active_id].get('amount')
				amount = before_amount + distribute + item.get('price_sum')
				before_person_count = active_money_map[active_id].get('person_count') 
				person_count = before_person_count + 1
			else:
				amount = distribute + item.get('price_sum')
				person_count = 1
			tmp = {}
			tmp['amount'] = amount
			tmp['person_count'] = person_count
			tmp['active_name'] = item['active_name']
			active_money_map[active_id] = tmp
		
		for key in active_money_map:
			res.append(active_money_map[key])
		data = {'actives': res, 'active_num': active_num}
		return {'code': 0, 'data': data}

@method_decorator([standard_api(methods=('GET', 'POST'))], name='dispatch')
class StoreActiveverSalerAPI(View):
    def get(self, request):
    	params = request.GET
    	store_id = int(params.get('store_id'))
    	active_id = int(params.get('active_id'))
    	user = utils.request_user(request)
    	amap = None
    	try:
    		amap = ActiveStoreMap.objects.get(store_id=store_id, active_id=active_id)
    	except Exception as e:
    		return {'code': 1, 
    				'data': '服务器数据异常门店：%s,活动：%s' % (str(store_id), str(active_id))}
    	count = ActiveLog.objects.filter(customer_id=user.id, 
    									 active_map=amap.id).count()
    	if count > 0:
    		return {'code': 2, 'data': u'您已参加了该活动,不能重复参加'}
        if active_id == 2:
            today = timezone.now()
            year = today.year
            month = today.month
            day = today.day
            today_count = ActiveLog.objects.filter(time__year=year,
                                          time__month=month,
                                          time__day=day, 
                                         active_map=amap.id).count()
            if today_count >= 300:
                return {'code': 3,'data': u'今日名额已满'}

            # return {'code': 3, 'data': u'今日名额已满'}
    	sql = """
    		SELECT 
    			saler.name, saler.id
    		FROM 
    			shangmi_activestoremap AS mp
    		LEFT JOIN 
    			shangmi_storesalermap as smp
    		ON
    			mp.store_id=smp.store_id
    		LEFT JOIN
    			shangmi_saler AS saler
    		ON
    			smp.saler_id=saler.id
    		LEFT JOIN 
    			shangmi_user as u
    		ON 
    			u.id=saler.user_id
    		WHERE
    			saler.status=0
    		AND 
    			mp.store_id={store_id}
    		AND
    			mp.active_id={active_id};
    	""".format(store_id=store_id, active_id=active_id)
    	cur = connection.cursor()
        cur.execute(sql)
        salers = utils.dictfetchall(cur)
        # images = ActiveImages.objects.get(active_id=active_id)
        data = {'salers': salers, 'images': []}
        if active_id == 1:
            try:
                price_log = CustomerGetPriceLog.objects.get(
                    customer=user,
                    active_id=active_id,
                    store_id=store_id)
                random_price = price_log.price
            except Exception as e:
                active_range = ActiveRandomRange.objects.get(active_id=active_id)
                random_price = float('%.1f' % random.uniform(
                    active_range.random_start, active_range.random_end))
                log = CustomerGetPriceLog.objects.create(
                   customer=user,
                   price=random_price,
                   store_id=store_id,
                   active_id=active_id,
                   add_time=timezone.now())
            data['random_price'] = random_price
        if active_id == 2:
            # try:
            #     phone = params.get('phone')
            #     UserConfirmPhone.objects.get(
            #         phone=phone, 
            #         is_used=False, 
            #         active_id=active_id)
            # except Exception as e:
            #     print e
            #     return {'code': 2, 'data': u'您的手机号不满足条件'}
            try:
                price_log = CustomerGetPriceLog.objects.get(
                    customer=user,
                    active_id=active_id,
                    store_id=store_id)
                random_price = price_log.price
            except Exception as e:
                active_range = ActiveRandomRange.objects.get(active_id=active_id)
                random_price = float('%.1f' % random.uniform(
                    active_range.random_start, active_range.random_end))
                log = CustomerGetPriceLog.objects.create(
                   customer=user,
                   price=random_price,
                   store_id=store_id,
                   active_id=active_id,
                   add_time=timezone.now())
            data['random_price'] = random_price
        return {'code': 0, 'data': data}


@method_decorator([standard_api(methods=('GET', 'POST'))], name='dispatch')
class RegisteAPI(View):
    def post(self, request):
    	params = QueryDict(request.body)
    	user = utils.request_user(request)
    	phone = params.get('phone')
    	try:
    		register = Saler.objects.get(phone=phone)

    		try:
	    		register.status = 0
	    		register.user = user
	    		register.save()
	    	except Exception as e:
    			print e
    		
    		smp = StoreSalerMap.objects.get(saler=register)
    		identity = 'saler'
    		if register.is_boss == True:
    			identity = 'boss'
    		data = {'identity': identity, 'store_id': smp.store.id}
    		return {'code': 0, 'data': data}
    	except:
    		try:
    			register = Store.objects.get(phone=phone)
    			register.boss = user
    			register.status = 0
    			register.save()
    			#火车新增
    			saler = Saler.objects.get_or_create(
    				user=user,
    				name=u'店长',
    				phone=register.phone,
    				status=0)[0]
    			saler.is_boss = True
    			saler.save()
    			ssmp = StoreSalerMap.objects.get_or_create(
    				saler_id=saler.id,
    				store_id=register.id)[0]
    			ssmp.save()
    			data = {'identity': 'boss', 'store_id': register.id}
    			return {'code': 0, 'data': data}
    		except Exception as e:
    			print e
    			return {'code': 1, 'data': '无此账号'}

@method_decorator([standard_api(methods=('GET', 'POST'))], name='dispatch')
class SalerAPI(View):
    def post(self, request):
    	params = QueryDict(request.body)
    	user = utils.request_user(request)
    	store = Store.objects.get(boss=user)
    	name = params.get('name')
    	phone = params.get('phone')
    	saler = Saler.objects.get_or_create(
    		name=name, 
    		phone=phone,
    		status=2)[0]
    	saler.save()
    	smp = StoreSalerMap.objects.create(
    		saler=saler,
    		store=store)
    	smp.save()
    	return {'code': 0, 'data': u'新增成功'}

    def get(self, request):
        params = request.GET
        store_id = int(params.get('store_id'))
        maps = StoreSalerMap.objects.filter(store_id=store_id)
        results = []
        for data in maps:
        	if data.saler:
	        	tmp = model_to_dict(data.saler)
	        	tmp['id'] = data.saler.id
        		results.append(tmp)
        results =  sorted(results, key=lambda x:x['status'])
        return {'data': results}


@method_decorator([standard_api(methods=('GET', 'POST'))], name='dispatch')
class BossActiveverviewAPI(View):
    def get(self, request):
    	params = request.GET
    	user = utils.request_user(request)
    	store_id = int(params.get('store_id'))
        active_id = int(params.get('active_id'))
    	data_type = params.get('data_type')
    	identity = params.get('identity')

    	active_num = ActiveStoreMap.objects.filter(
    		store_id=store_id, 
    		active__status=1).count()
    	res = []
    	if identity == 'boss':
			item_detail_list = utils.get_store_active_v1(store_id, data_type, active_id)
    	else:
    		saler = Saler.objects.get(user=user)
        	item_detail_list = utils.get_saler_active_v1(
        		store_id, 
        		data_type, 
        		saler.id,
                active_id)
        data = {'actives': item_detail_list}
        # print data
        return {'code': 0, 'data': data}


@method_decorator([standard_api(methods=('GET', 'POST'))], name='dispatch')
class WriteoffAPI(View):
    def post(self, request):
        params = QueryDict(request.body)
        user = utils.request_user(request)
        sid = int(params.get('sid'))
        store_id = int(params.get('store_id'))
        active_id = int(params.get('active_id'))
        try:
            price_log = CustomerGetPriceLog.objects.get(
            customer=user, 
            active_id=active_id, 
            store_id=store_id)
        except Exception as e:
            return {'code': 2, 'data': '您的账号异常'}
        asmap = ActiveStoreMap.objects.get(
			store_id=store_id, 
			active_id=active_id)
        check = ActiveLog.objects.filter(
            active_map_id=asmap.id,
            customer=user).count()
        if check > 0:
            return {'code': 2, 'data':u'此人已参加该活动'}
        if active_id == 2:
            phone = params.get('phone')
            # try:
            #     ucp = UserConfirmPhone.objects.get(
            #         phone=phone,
            #         active_id=active_id)
            #     ucp.is_used = True
            #     ucp.used_time = timezone.now()
            #     ucp.save()
            # except Exception as e:
            #     return {'code': 2, 'data': '您的手机号异常'}

        log = ActiveLog.objects.create(
			active_map_id=asmap.id, 
			saler_id=sid, 
			customer=user,
            customer_get_price_log=price_log)
        price_log.is_writeoff = True
        price_log.update_time = timezone.now()
        price_log.save()
        log.save()
        return {'data': 'ok'}


@method_decorator([standard_api(methods=('GET', ))], name='dispatch')
class QrcodeAPI(View):
    def get(self, request):
        params = request.GET
        active_id = int(params.get('active_id'))
        store_id = int(params.get('store_id'))
        wx_mini_path = 'pages/bind_phone/bind_phone?store_id=%s&active_id=%s' % (store_id, active_id)
        image_data = getqr.get_qrcode(wx_mini_path)
        return HttpResponse(image_data,content_type="image/png")


@method_decorator([standard_api(methods=('GET', 'POST'))], name='dispatch')
class AdjustAccountsAPI(View):
    def get(self, request):
        params = request.GET
        active_id = int(params.get('active_id'))
        store_id = int(params.get('store_id'))
        # active_map = ActiveStoreMap.objects.get(
        #     store_id=store_id, 
        #     active_id=active_id)
        # sql = """
        #     SELECT 
        #         sum(plog.price) AS money
        #     FROM 
        #         shangmi_activelog as alog
        #     LEFT JOIN
        #         shangmi_customergetpricelog as plog
        #     ON
        #         alog.customer_get_price_log_id=plog.id
        #     WHERE 
        #         alog.is_writeoff=FALSE
        #     AND
        #         active_map_id={active_map_id}
        #     AND
        #         plog.is_writeoff=TRUE
        # """.format(active_map_id=active_map.id)
        # cur = connection.cursor()
        # cur.execute(sql)
        # money = utils.dictfetchall(cur)[0].get('money')
        # if not money:
        #     money = 0
        try:
            account = AdjustAccounts.objects.filter(
                store_id=store_id, 
                active_id=active_id).order_by('-time')[0]
            account_time = account.time.strftime("%Y-%m-%d")
        except Exception as e:
            account_time = ''	
        advance_sum = 0
        money = 0
        datas = utils.get_store_active_v1(store_id, 'all', active_id)
        for data in datas:
        	money += data['distribute']
        	advance_sum += data['price_sum']
        return {'data': {'money': money,'advance_sum': advance_sum, 'last_adjust_time': account_time}}

    def post(self, request):
        params = QueryDict(request.body)
        store_id = int(params.get('store_id'))
        active_id = int(params.get('active_id'))
        date = params.get('date')
        date = datetime.datetime.strptime(date, "%Y-%m-%d")
        price = float(params.get('price'))
        user = utils.request_user(request)
        smap = ActiveStoreMap.objects.get(
            active_id=active_id, 
            store_id=store_id)
        now = timezone.now()
        # logs = ActiveLog.objects.filter(active_map=smap)
        # sql = """
        #     SELECT
        #         log.id,
        #         price_log.price as price
        #     FROM
        #         shangmi_activelog as log
        #     LEFT JOIN
        #         shangmi_customergetpricelog as price_log
        #     ON
        #         log.customer_get_price_log_id=price_log.id
        #     WHERE 
        #         log.is_writeoff=FALSE
        #     AND
        #         log.active_map_id={smap_id}
        #     AND
        #         log.time<='{date_time}'
        # """.format(smap_id=smap.id, date_time=date)
        
        # cur = connection.cursor()
        # cur.execute(sql)
        # logs = utils.dictfetchall(cur)
        # price_sum = 0
        # for log in logs:
        #     if log.get('price'):
        #         price_sum += log.get('price')
        account = AdjustAccounts.objects.create(
            adminor=user,
            store_id=store_id,
            active_id=active_id,
            price=price)
        account.save()
        # times = ActiveLog.objects.filter(active_map=smap, 
        #     is_writeoff=False)
        # for l in times:
        # 	print str(l.time) <= str(date)
        # print time,type(time)
        logs = ActiveLog.objects.filter(
            active_map=smap, 
            is_writeoff=False,
            time__lte=date).update(
            is_writeoff=True)
        return {'data': 'ok'}


@method_decorator([standard_api(methods=('GET', 'POST'))], name='dispatch')
class ActiveImageAPI(View):
    def get(self, request):
        params = request.GET
        active_id = int(params.get('active_id'))
        active_image = ActiveImages.objects.get(active_id=active_id)
        return {'data': model_to_dict(active_image)}


# 火车新增	
@method_decorator([standard_api(methods=('GET'))], name='dispatch')
class StoreMoneyViewAPI(View):
	#赏米未结算余额
    def get(self, request):
    	params = request.GET
    	user = utils.request_user(request)
    	store_id = int(params.get('store_id'))
    	identity = params.get('identity')
    	if identity == 'boss':
    		money = utils.get_boss_money(store_id)
    	if identity == 'saler':
    		smap = StoreSalerMap.objects.get(
    			saler__user_id=user.id,
    			store_id=store_id)
    		money = utils.get_saler_money(store_id,smap.saler.id)
    	date = datetime.datetime.now().day
    	text = u'还未到提现日期哦'
    	if date == 12:
    		text = u'提现将由人工处理'
    	return {'data':{'money':money, 'confirmText': text}}


@method_decorator([standard_api(methods=('GET', 'POST'))], name='dispatch')
class RecordsDetailAPI(View):
    def get(self, request):
        params = request.GET
        user = utils.request_user(request)
        store_id = int(params.get('store_id'))
        identity = params.get('identity')
        # StoreSalerMap.objects.filter()
        if identity == 'boss':
    		results = utils.get_boss_records_detail(store_id)
    		return {'data': results}
    	if identity == 'saler':
    		smap = StoreSalerMap.objects.get(
    			saler__user_id=user.id,
    			store_id=store_id)
    		results = utils.get_saler_records_detail(store_id, smap.saler.id)
    		return {'data': results}

@method_decorator([standard_api(methods=('GET', 'POST'))], name='dispatch')
class ActivePhoneAPI(View):
    def get(self, request):
        params = request.GET
        phone = params.get('phone')
        active_id = int(params.get('active_id'))
        obj, created = UserConfirmPhone.objects.get_or_create(phone=phone,active_id=active_id)
        if created:
            return {'code':0, 'data': phone, 'msg': u'success'}
        else:
            return {'code':1, 'data': phone, 'msg': u'exist'}


@method_decorator([standard_api(methods=('GET', 'POST'))], name='dispatch')
class TixianAPI(View):
    def get(self, request):
        params = request.GET
        user = utils.request_user(request)
        # openid = 