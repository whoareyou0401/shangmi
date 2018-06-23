# -*- coding: utf-8 -*-
from django.conf import settings
from itsdangerous import URLSafeTimedSerializer as utsr
from django.db import connection
from django.utils import timezone
from django.http import HttpResponse, QueryDict
import base64
import requests
import six
import models
import socket
import hashlib
import xmltodict
import json
from datetime import datetime


def sign(params, sign_key="6C57AB91A1308E26B797F4CD382AC79D"):
    method = params.get('method')
    params = [(u'%s' % key, u'%s' % val) for key, val in params.iteritems() if val]
    params = sorted(params)
    sorted_params_string = ''.join(''.join(pair) for pair in params)
    sign_str = method + sorted_params_string + sign_key,
    md5 = hashlib.md5()
    md5.update(sign_str[0])
    return md5.hexdigest().upper()


def get_local_ip():
    myname = socket.getfqdn(socket.gethostname())
    myaddr = socket.gethostbyname(myname)
    return myaddr


def pay_sign(params, sign_key):
    params = [(u'%s' % key, u'%s' % val) for key, val in params.iteritems() if val]
    sorted_params_string = '&'.join('='.join(pair) for pair in sorted(params))
    sign = '{}&key={}'.format(sorted_params_string.encode('utf-8'), sign_key)
    md5 = hashlib.md5()
    md5.update(sign)
    return md5.hexdigest().upper()


def get_actives():
    url = "https://mcp.ddky.com/weixin/rest.htm"
    date = datetime.now()
    date = str(date).split('.')[0]
    request_data = {
        'activityId':587,
        'city':'beijing',
        'lat':39.91488908,
        'lng':116.40387397,
        'method':'ddky.promotion.onebuy.new.activity.pageinfo',
        'pageType':1,
        'plat':'H5',
        'platform':'H5',
        't': date,
        'v':'1.0',
        'versionName':'3.5.0'
    }
    end_url = get_url(url, request_data)
    response = requests.get(end_url)
    res = None
    try:
        json_str = re.findall(r'[^()]+', response.content)[1]
        res = json.loads(json_str)
        # print res,'res ok'
    except Exception as e:
        res = json.loads(response.content)
    return res

def xml_response_to_dict(rep):
    d = xmltodict.parse(rep.content)
    return dict(d['response'])


def get_phone_area(phone):
    url = 'http://i.ataohao.com/api/hw?cmd=80100031&param=%3Cnumber%3E{phone}%3C/number%3E%3Ctype%3E1%3C/type%3E'.format(
        phone=phone)
    res = requests.get(url=url)
    data = xml_response_to_dict(res)
    return data.get('locInfo')


def get_url(url, params):
    
    p = ''
    for key in params:
        p += "&" + key + "=" + str(params.get(key))
    sign_str = sign(params)
    p = url + '?sign=' +sign_str + p
    return p


def dictfetchall(cursor):
    "Return all rows from a cursor as a dict"
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]

def confirm_validate_token(token, expiration=settings.SMALL_WEIXIN_TOKEN_VALID_TIME):
    serializer = utsr(settings.SECRET_KEY)
    salt = base64.encodestring(settings.SECRET_KEY)
    return serializer.loads(token, salt=salt, max_age=expiration)


def generate_validate_token(openid):
    serializer = utsr(settings.SECRET_KEY)
    salt = base64.encodestring(settings.SECRET_KEY)
    return serializer.dumps(openid, salt)


def request_user(request):
    if request.method == "GET":
        token = request.GET.get('token')
    else:
        params = QueryDict(request.body)
        token = params.get('token')
    openid = confirm_validate_token(token)
    user = models.User.objects.get(openid=openid)
    return user


def distance_to_location(current_lng, current_lat, radius):
    add_lat = radius / settings.CM_DISCOVER_STORE_LAT_TO_DISTANCE
    add_lng = radius / settings.CM_DISCOVER_STORE_LNG_TO_DISTANCE
    radius_lat_location = add_lat / 3600
    radius_lng_location = add_lng / 3600
    start_lat = current_lat - radius_lat_location
    end_lat = current_lat + radius_lat_location
    start_lng = current_lng - radius_lng_location
    end_lng = current_lng + radius_lng_location
    return [start_lng, end_lng, start_lat, end_lat]


def search(key_word):
    sql = '''
    SELECT
        i.*
    FROM
      recommendorder_item as i
    WHERE
      i.item_id in ('%(item_ids)s') AND
      i.source = '%(source)s'
    '''
    cur = connection.cursor()
    cur.execute(sql, {'item_ids': "','".join(item_list), 'source': source})
    item_detail_list = dictfetchall(cur)


def get_models_by_postion(position):
    sql = '''
    SELECT
        models.*,
        unlike.unlikes,
        likes.likes
    FROM "yalongApp_ylmodel" as models
      LEFT JOIN (SELECT count(ulike.id) unlikes ,ulike.collecteder_id
      FROM "yalongApp_unlike" AS ulike LEFT JOIN "yalongApp_ylmodel" as model
      ON collecteder_id=model.id
      GROUP BY collecteder_id) AS unlike
      ON unlike.collecteder_id=models.id
      LEFT JOIN (SELECT count(li.id) likes ,li.collecteder_id
      FROM "yalongApp_like" AS li LEFT  JOIN "yalongApp_ylmodel" as model1
      ON li.collecteder_id=model1.id
      GROUP BY collecteder_id) AS likes
      ON likes.collecteder_id=models.id
    WHERE
      models.position=1
    '''
    cur = connection.cursor()
    cur.execute(sql, {'position': position })
    item_detail_list = dictfetchall(cur)


def dictfetchall(cursor):
    "Return all rows from a cursor as a dict"
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]


def __category_names_to_ids(names):
    cursor = connection.cursor()
    cursor.execute("""
        SELECT array_agg(id) as categories from standard_category where (%s)
    """ % ' or '.join(["name='%s'" % n for n in names]))
    result = dictfetchall(cursor)
    return result[0]['categories']


def __extract_operator(key):
    toks = key.split('__')
    if len(toks) == 2:
        return toks[0], toks[1]
    return key, None


def __convert_to_sql(k, v):
    if v['splitter'] == 'or':
        sub = []
        if k == 'category_id':
            v['value'] = __category_names_to_ids(v['value'])

        for i in v['value']:
            sub.append("%s='%s'" % (k, i))
        return '(%s)' % ' or '.join(sub)
    elif v['splitter'] == 'between':
        return "(%s between '%s' and '%s')" % (k, v['value'][0], v['value'][1])


def __strip_each(l):
    return [val.strip() for val in l]


def growth_rate(rate):
    if rate:
        return '+%.2f' % rate if rate > 0 else '%.2f' % rate


def query_builder(q, m):
    toks = q.split('@')
    d = {}
    for t in toks:
        kv = t.strip().split('=')
        if len(kv) != 2:
            continue
        key = kv[0].strip()
        key, opeartor = __extract_operator(key)
        if key in m:
            if opeartor and opeartor == u'在':
                values = kv[1].split('~')
                if len(values) != 2:
                    continue
                d[m[key]] = {'splitter': 'between',
                             'value': __strip_each(values)}
            else:
                d[m[key]] = {'splitter': 'or',
                             'value': __strip_each(kv[1].split(','))}

    out = []
    for key, values in d.items():
        out.append(__convert_to_sql(key, values))
    return ' and '.join(out)


def construct_where_clause(filter_dict, params):

    def handle_single_filter(key):
        if key.endswith('__contains'):
            filter_dict[key] = '%' + filter_dict[key] + '%'
            col_name = key[0: -len('__contains')]
            return '%s LIKE %%(%s)s' % (col_name, key)
        if key.endswith('__lt'):
            col_name = key[0: -len('__lt')]
            return '%s<%%(%s)s' % (col_name, key)
        if key.endswith('__gt'):
            col_name = key[0: -len('__gt')]
            return '%s>%%(%s)s' % (col_name, key)
        else:
            return '%s = %%(%s)s' % (key, key)

    if filter_dict is None or len(filter_dict) == 0:
        return ''
    clauses = [handle_single_filter(k) for k in filter_dict.keys()]
    for k, v in six.iteritems(filter_dict):
        params[k] = v
    return '\nWHERE ' + "\n AND \n\t".join(clauses)


def get_store_active_v1(store_id, data_type, active_id):
    if data_type == 'today':
        today = timezone.now().date()
        sql = """
                SELECT 
                    m.store_id, 
                    m.active_id, 
                    u.phone,
                    to_char(log.time, 'YYYY-MM-DD HH24:MI:SS') AS time,
                    active.name AS active_name,
                    saler.name AS saler_name,
                    plog.price AS price_sum,
                    saler.is_boss
                FROM 
                    shangmi_activestoremap AS m 
                LEFT JOIN 
                    shangmi_activelog AS log 
                ON 
                    m.id=log.active_map_id 
                LEFT JOIN 
                    shangmi_active AS active 
                ON 
                    m.active_id=active.id 
                LEFT JOIN 
                    shangmi_saler AS saler
                ON
                    saler.id=log.saler_id
                LEFT JOIN
                    shangmi_customergetpricelog as plog
                ON
                    log.customer_get_price_log_id=plog.id
                LEFT JOIN 
                    shangmi_user AS u
                ON
                    plog.customer_id=u.id
                WHERE 
                    m.store_id={store_id}
                AND 
                    active.status=1  
                AND 
                    log.is_writeoff=FALSE
                AND 
                    log.time::date='{date}'
                AND 
                    active.id={active_id}
                AND 
                    plog.is_writeoff=TRUE;
            """.format(store_id=store_id, date=today, active_id=active_id)
    elif data_type == 'all':
        sql = """
                SELECT 
                    m.store_id, 
                    m.active_id, 
                    u.phone,
                    to_char(log.time, 'YYYY-MM-DD HH24:MI:SS') AS time,
                    active.name AS active_name,
                    saler.name AS saler_name,
                    plog.price AS price_sum,
                    saler.is_boss
                FROM 
                    shangmi_activestoremap AS m 
                LEFT JOIN 
                    shangmi_activelog AS log 
                ON 
                    m.id=log.active_map_id 
                LEFT JOIN 
                    shangmi_active AS active 
                ON 
                    m.active_id=active.id 
                LEFT JOIN 
                    shangmi_saler AS saler
                ON
                    saler.id=log.saler_id
                LEFT JOIN
                    shangmi_customergetpricelog as plog
                ON
                    log.customer_get_price_log_id=plog.id
                LEFT JOIN 
                    shangmi_user AS u
                ON
                    plog.customer_id=u.id
                WHERE 
                    m.store_id={store_id}
                AND 
                    active.status=1  
                AND 
                    plog.is_writeoff=TRUE
                AND 
                    log.is_writeoff=FALSE
                AND 
                    active.id={active_id};
        """.format(store_id=store_id, active_id=active_id)
    elif data_type == 'history':
        sql = """
                SELECT 
                    m.store_id, 
                    m.active_id, 
                    u.phone,
                    to_char(log.time, 'YYYY-MM-DD HH24:MI:SS') AS time,
                    active.name AS active_name,
                    saler.name AS saler_name,
                    plog.price AS price_sum,
                    saler.is_boss
                FROM 
                    shangmi_activestoremap AS m 
                LEFT JOIN 
                    shangmi_activelog AS log 
                ON 
                    m.id=log.active_map_id 
                LEFT JOIN 
                    shangmi_active AS active 
                ON 
                    m.active_id=active.id 
                LEFT JOIN 
                    shangmi_saler AS saler
                ON
                    saler.id=log.saler_id
                LEFT JOIN
                    shangmi_customergetpricelog as plog
                ON
                    log.customer_get_price_log_id=plog.id
                LEFT JOIN 
                    shangmi_user AS u
                ON
                    plog.customer_id=u.id
                WHERE 
                    m.store_id={store_id}
                AND 
                    active.status=1  
                AND 
                    log.is_writeoff=TRUE
                AND 
                    plog.is_writeoff=TRUE
                AND 
                    active.id={active_id}
                ;
        """.format(store_id=store_id, active_id=active_id)
    else:
        return []
    cur = connection.cursor()
    cur.execute(sql)
    item_detail_list = dictfetchall(cur)
    distribute = models.StoreMoneyDistribution.objects.get(
        active_id=active_id)
    for data in item_detail_list:
        if data.get('is_boss') == True:
            data['distribute'] = distribute.boss_money 
        else:
            data['distribute'] = distribute.boss_distribute_money
        data['phone'] = data['phone'][0:3]+ '****'+ data['phone'][7:]
    return item_detail_list


def get_store_active(store_id, data_type, active_id):
    if data_type == 'today':
        today = timezone.now().date()
        sql = """
                SELECT 
                    m.store_id, 
                    m.active_id, 
                    count(log.customer_id) AS num,
                    MAX(active.name) AS active_name,
                    max(saler.name) AS saler_name,
                    sum(plog.price) AS price_sum
                FROM 
                    shangmi_activestoremap AS m 
                LEFT JOIN 
                    shangmi_activelog AS log 
                ON 
                    m.id=log.active_map_id 
                LEFT JOIN 
                    shangmi_active AS active 
                ON 
                    m.active_id=active.id 
                LEFT JOIN 
                    shangmi_saler AS saler
                ON
                    saler.id=log.saler_id
                LEFT JOIN
                    shangmi_customergetpricelog as plog
                ON
                    log.customer_get_price_log_id=plog.id
                WHERE 
                    m.store_id={store_id}
                AND 
                    active.status=1  
                AND 
                    log.is_writeoff=FALSE
                AND 
                    log.time::date='{date}'
                AND 
                    active.id={active_id}
                AND 
                    plog.is_writeoff=TRUE
                GROUP BY 
                    m.store_id, m.active_id, log.saler_id;
            """.format(store_id=store_id, date=today, active_id=active_id)
    elif data_type == 'all':
        sql = """
                SELECT 
                    m.store_id, 
                    m.active_id, 
                    count(log.customer_id) AS num,
                    MAX(active.name) AS active_name,
                    max(saler.name) AS saler_name,
                    sum(plog.price) AS price_sum
                FROM 
                    shangmi_activestoremap AS m 
                LEFT JOIN 
                    shangmi_activelog AS log 
                ON 
                    m.id=log.active_map_id 
                LEFT JOIN 
                    shangmi_active AS active 
                ON 
                    m.active_id=active.id 
                LEFT JOIN 
                    shangmi_saler AS saler
                ON
                    saler.id=log.saler_id
                LEFT JOIN
                    shangmi_customergetpricelog as plog
                ON
                    log.customer_get_price_log_id=plog.id
                WHERE 
                    m.store_id={store_id}
                AND 
                    active.status=1  
                AND 
                    plog.is_writeoff=TRUE
                AND 
                    log.is_writeoff=FALSE
                AND 
                    active.id={active_id}
                GROUP BY 
                    m.store_id, m.active_id, log.saler_id;
        """.format(store_id=store_id, active_id=active_id)
    elif data_type == 'history':
        sql = """
                SELECT 
                    m.store_id, 
                    m.active_id, 
                    count(log.customer_id) AS num,
                    MAX(active.name) AS active_name,
                    max(saler.name) AS saler_name,
                    sum(plog.price) AS price_sum
                FROM 
                    shangmi_activestoremap AS m 
                LEFT JOIN 
                    shangmi_activelog AS log 
                ON 
                    m.id=log.active_map_id 
                LEFT JOIN 
                    shangmi_active AS active 
                ON 
                    m.active_id=active.id 
                LEFT JOIN 
                    shangmi_saler AS saler
                ON
                    saler.id=log.saler_id
                LEFT JOIN
                    shangmi_customergetpricelog as plog
                ON
                    log.customer_get_price_log_id=plog.id
                WHERE 
                    m.store_id={store_id}
                AND 
                    active.status=1  
                AND 
                    log.is_writeoff=TRUE
                AND 
                    plog.is_writeoff=TRUE
                AND 
                    active.id={active_id}
                GROUP BY 
                    m.store_id, m.active_id, log.saler_id;
        """.format(store_id=store_id, active_id=active_id)
    else:
        return []
    cur = connection.cursor()
    cur.execute(sql)
    item_detail_list = dictfetchall(cur)
    return item_detail_list


def get_saler_active_v1(store_id, data_type, saler_id, active_id):
    if data_type == 'today':
        today = timezone.now().date()
        sql = """
                SELECT 
                    m.store_id, 
                    m.active_id, 
                    u.phone,
                    to_char(log.time, 'YYYY-MM-DD HH24:MI:SS') AS time,
                    active.name AS active_name,
                    saler.name AS saler_name,
                    plog.price AS price_sum,
                    saler.is_boss
                FROM 
                    shangmi_activestoremap AS m 
                LEFT JOIN 
                    shangmi_activelog AS log 
                ON 
                    m.id=log.active_map_id 
                LEFT JOIN 
                    shangmi_active AS active 
                ON 
                    m.active_id=active.id 
                LEFT JOIN 
                    shangmi_saler AS saler
                ON
                    saler.id=log.saler_id
                LEFT JOIN
                    shangmi_customergetpricelog as plog
                ON
                    log.customer_get_price_log_id=plog.id
                LEFT JOIN 
                    shangmi_user AS u
                ON
                    plog.customer_id=u.id
                WHERE 
                    m.store_id={store_id}
                AND 
                    active.status=1  
                AND
                    saler.id={saler_id}
                AND 
                    active.id={active_id}
                AND 
                    plog.is_writeoff=TRUE
                AND 
                    log.is_writeoff=FALSE
                AND 
                    log.time::date='{date}'
                    
            """.format(store_id=store_id, 
                       date=today, 
                       saler_id=saler_id, 
                       active_id=active_id)
    elif data_type == 'all':
        sql = """
                SELECT 
                    m.store_id, 
                    m.active_id, 
                    u.phone,
                    to_char(log.time, 'YYYY-MM-DD HH24:MI:SS') AS time,
                    active.name AS active_name,
                    saler.name AS saler_name,
                    plog.price AS price_sum,
                    saler.is_boss
                FROM 
                    shangmi_activestoremap AS m 
                LEFT JOIN 
                    shangmi_activelog AS log 
                ON 
                    m.id=log.active_map_id 
                LEFT JOIN 
                    shangmi_active AS active 
                ON 
                    m.active_id=active.id 
                LEFT JOIN 
                    shangmi_saler AS saler
                ON
                    saler.id=log.saler_id
                LEFT JOIN
                    shangmi_customergetpricelog as plog
                ON
                    log.customer_get_price_log_id=plog.id
                LEFT JOIN 
                    shangmi_user AS u
                ON
                    plog.customer_id=u.id
                WHERE 
                    m.store_id={store_id}
                AND 
                    active.status=1  
                AND 
                    plog.is_writeoff=TRUE
                AND 
                    log.is_writeoff=FALSE
                AND
                    saler.id={saler_id}
                AND 
                    active.id={active_id};
        """.format(store_id=store_id, 
                   saler_id=saler_id, 
                   active_id=active_id)
    elif data_type == 'history':
        sql = """
                SELECT 
                    m.store_id, 
                    m.active_id, 
                    u.phone,
                    to_char(log.time, 'YYYY-MM-DD HH24:MI:SS') AS time,
                    active.name AS active_name,
                    saler.name AS saler_name,
                    plog.price AS price_sum,
                    saler.is_boss
                FROM 
                    shangmi_activestoremap AS m 
                LEFT JOIN 
                    shangmi_activelog AS log 
                ON 
                    m.id=log.active_map_id 
                LEFT JOIN 
                    shangmi_active AS active 
                ON 
                    m.active_id=active.id 
                LEFT JOIN 
                    shangmi_saler AS saler
                ON
                    saler.id=log.saler_id
                LEFT JOIN
                    shangmi_customergetpricelog as plog
                ON
                    log.customer_get_price_log_id=plog.id
                LEFT JOIN 
                    shangmi_user AS u
                ON
                    plog.customer_id=u.id
                WHERE 
                    m.store_id={store_id}
                AND 
                    active.status=1  
                AND 
                    plog.is_writeoff=TRUE
                AND 
                    log.is_writeoff=TRUE
                AND
                    saler.id={saler_id}
                AND 
                    active.id={active_id}
        """.format(store_id=store_id, 
                   saler_id=saler_id, 
                   active_id=active_id)
    cur = connection.cursor()
    cur.execute(sql)
    item_detail_list = dictfetchall(cur)
    distribute = models.StoreMoneyDistribution.objects.get(
        active_id=active_id)
    for data in item_detail_list:
        if data.get('is_boss') == True:
            data['distribute'] = distribute.boss_money 
        else:
            data['distribute'] = distribute.saler_money
        data['phone'] = data['phone'][0:3]+ '****'+ data['phone'][7:]
    return item_detail_list


def get_saler_active(store_id, data_type, saler_id, active_id):
    if data_type == 'today':
        today = timezone.now().date()
        sql = """
                SELECT 
                    m.store_id, 
                    m.active_id, 
                    count(log.customer_id) AS num,
                    MAX(active.name) AS active_name,
                    max(saler.name) AS saler_name,
                    sum(plog.price) AS price_sum
                FROM 
                    shangmi_activestoremap AS m 
                LEFT JOIN 
                    shangmi_activelog AS log 
                ON 
                    m.id=log.active_map_id 
                LEFT JOIN 
                    shangmi_active AS active 
                ON 
                    m.active_id=active.id 
                LEFT JOIN 
                    shangmi_saler AS saler
                ON
                    saler.id=log.saler_id
                LEFT JOIN
                    shangmi_customergetpricelog as plog
                ON
                    log.customer_get_price_log_id=plog.id
                WHERE 
                    m.store_id={store_id}
                AND 
                    active.status=1  
                AND
                    saler.id={saler_id}
                AND 
                    active.id={active_id}
                AND 
                    plog.is_writeoff=TRUE
                AND 
                    log.is_writeoff=FALSE
                AND 
                    log.time::date='{date}'
                GROUP BY 
                    m.store_id, m.active_id, log.saler_id;
            """.format(store_id=store_id, 
                       date=today, 
                       saler_id=saler_id, 
                       active_id=active_id)
    elif data_type == 'all':
        sql = """
                SELECT 
                    m.store_id, 
                    m.active_id, 
                    count(log.customer_id) AS num,
                    MAX(active.name) AS active_name,
                    max(saler.name) AS saler_name,
                    sum(plog.price) AS price_sum
                FROM 
                    shangmi_activestoremap AS m 
                LEFT JOIN 
                    shangmi_activelog AS log 
                ON 
                    m.id=log.active_map_id 
                LEFT JOIN 
                    shangmi_active AS active 
                ON 
                    m.active_id=active.id 
                LEFT JOIN 
                    shangmi_saler AS saler
                ON
                    saler.id=log.saler_id
                LEFT JOIN
                    shangmi_customergetpricelog as plog
                ON
                    log.customer_get_price_log_id=plog.id
                WHERE 
                    m.store_id={store_id}
                AND 
                    active.status=1  
                AND 
                    plog.is_writeoff=TRUE
                AND 
                    log.is_writeoff=FALSE
                AND
                    saler.id={saler_id}
                AND 
                    active.id={active_id}
                GROUP BY 
                    m.store_id, m.active_id, log.saler_id;
        """.format(store_id=store_id, 
                   saler_id=saler_id, 
                   active_id=active_id)
    elif data_type == 'history':
        sql = """
                SELECT 
                    m.store_id, 
                    m.active_id, 
                    count(log.customer_id) AS num,
                    MAX(active.name) AS active_name,
                    max(saler.name) AS saler_name,
                    sum(plog.price) AS price_sum
                FROM 
                    shangmi_activestoremap AS m 
                LEFT JOIN 
                    shangmi_activelog AS log 
                ON 
                    m.id=log.active_map_id 
                LEFT JOIN 
                    shangmi_active AS active 
                ON 
                    m.active_id=active.id 
                LEFT JOIN 
                    shangmi_saler AS saler
                ON
                    saler.id=log.saler_id
                LEFT JOIN
                    shangmi_customergetpricelog as plog
                ON
                    log.customer_get_price_log_id=plog.id
                WHERE 
                    m.store_id={store_id}
                AND 
                    active.status=1  
                AND 
                    plog.is_writeoff=TRUE
                AND 
                    log.is_writeoff=TRUE
                AND
                    saler.id={saler_id}
                AND 
                    active.id={active_id}
                GROUP BY 
                    m.store_id, m.active_id, log.saler_id;
        """.format(store_id=store_id, 
                   saler_id=saler_id, 
                   active_id=active_id)
    cur = connection.cursor()
    cur.execute(sql)
    item_detail_list = dictfetchall(cur)
    return item_detail_list

def get_boss_money(store_id):
    sql = """
        SELECT 
                m.store_id, 
                m.active_id, 
                log.customer_id,
                active.name AS active_name,
                saler.name AS saler_name,
                saler.is_boss AS is_boss,
                plog.price AS price_sum,
                to_char(log.time, 'YYYY-MM-DD HH24:MI:SS') AS time
            FROM 
                shangmi_activestoremap AS m 
            LEFT JOIN 
                shangmi_activelog AS log 
            ON 
                m.id=log.active_map_id 
            LEFT JOIN 
                shangmi_active AS active 
            ON 
                m.active_id=active.id 
            LEFT JOIN 
                shangmi_saler AS saler
            ON
                saler.id=log.saler_id
            LEFT JOIN
                shangmi_customergetpricelog as plog
            ON
                log.customer_get_price_log_id=plog.id
            WHERE 
                m.store_id={store_id}
            AND 
                active.status=1  
            AND 
                plog.is_writeoff=TRUE
            AND 
                log.is_writeoff=FALSE;
    """.format(store_id=store_id)
    cur = connection.cursor()
    cur.execute(sql)
    active_list = dictfetchall(cur)
    money_sum = 0
    advance_sum = 0
    for i in active_list:
        active_id = int(i.get('active_id'))
        distribute = models.StoreMoneyDistribution.objects.get(
        active_id=active_id)
        if i.get('is_boss') == True:
            money_sum += distribute.boss_money  
        else:
            money_sum += distribute.boss_distribute_money
        advance_sum += i['price_sum']
    return {'data': {'money_sum': money_sum, 'advance_sum': advance_sum}}


def get_saler_money(store_id, saler_id):
    sql = """
        SELECT 
                m.store_id, 
                m.active_id, 
                log.customer_id,
                active.name AS active_name,
                saler.name AS saler_name,
                saler.is_boss AS is_boss,
                plog.price AS price_sum,
                to_char(log.time, 'YYYY-MM-DD HH24:MI:SS') AS time
            FROM 
                shangmi_activestoremap AS m 
            LEFT JOIN 
                shangmi_activelog AS log 
            ON 
                m.id=log.active_map_id 
            LEFT JOIN 
                shangmi_active AS active 
            ON 
                m.active_id=active.id 
            LEFT JOIN 
                shangmi_saler AS saler
            ON
                saler.id=log.saler_id
            LEFT JOIN
                shangmi_customergetpricelog as plog
            ON
                log.customer_get_price_log_id=plog.id
            WHERE 
                m.store_id={store_id}
            AND 
                active.status=1  
            AND
                saler.id={saler_id}
            AND 
                plog.is_writeoff=TRUE
            AND 
                log.is_writeoff=FALSE;
    """.format(store_id=store_id, saler_id=saler_id)
    cur = connection.cursor()
    cur.execute(sql)
    active_list = dictfetchall(cur)
    money_sum = 0
    advance_sum = 0
    for i in active_list:
        active_id = int(i.get('active_id'))
        distribute = models.StoreMoneyDistribution.objects.get(
        active_id=active_id)
        if i.get('is_boss') == True:
            money_sum += distribute.boss_money  
        else:
            money_sum += distribute.boss_distribute_money
        advance_sum += i['price_sum']
    return {'data': {'money_sum': money_sum, 'advance_sum': advance_sum}}



def get_boss_records_detail(store_id):
    sql = """
            SELECT 
                m.store_id, 
                m.active_id, 
                log.customer_id,
                u.phone,
                active.name AS active_name,
                saler.name AS saler_name,
                saler.is_boss AS is_boss,
                to_char(log.time, 'YYYY-MM-DD HH24:MI:SS') AS time,
                plog.price AS price_sum
            FROM 
                shangmi_activestoremap AS m 
            LEFT JOIN 
                shangmi_activelog AS log 
            ON 
                m.id=log.active_map_id 
            LEFT JOIN 
                shangmi_active AS active 
            ON 
                m.active_id=active.id 
            LEFT JOIN 
                shangmi_saler AS saler
            ON
                saler.id=log.saler_id
            LEFT JOIN
                shangmi_customergetpricelog as plog
            ON
                log.customer_get_price_log_id=plog.id
            LEFT JOIN 
                shangmi_user AS u
            ON
                plog.customer_id=u.id
            WHERE 
                m.store_id={store_id}
            AND 
                active.status=1  
            AND 
                plog.is_writeoff=TRUE
            AND 
                log.is_writeoff=FALSE
            ORDER BY
                active.id;
    """.format(store_id=store_id)
    cur = connection.cursor()
    cur.execute(sql)
    active_list = dictfetchall(cur)
    # money_sum = 0
    # advance_sum = 0
    for i in active_list:
        active_id = int(i.get('active_id'))
        i['phone'] = i['phone'][0:3]+ '****'+ i['phone'][7:]
        distribute = models.StoreMoneyDistribution.objects.get(
        active_id=active_id)
        if i.get('is_boss') == True:
            i['distribute'] = distribute.boss_money  
        else:
            i['distribute'] = distribute.boss_distribute_money
    #     advance_sum += i['price_sum']
    return {'data': active_list}


def get_store_active_log(store_id, data_type):
    if data_type == 'today':
        today = timezone.now().date()
        sql = """
                SELECT 
                    m.store_id, 
                    m.active_id, 
                    u.phone,
                    to_char(log.time, 'YYYY-MM-DD HH24:MI:SS') AS time,
                    active.name AS active_name,
                    saler.name AS saler_name,
                    plog.price AS price_sum,
                    saler.is_boss
                FROM 
                    shangmi_activestoremap AS m 
                LEFT JOIN 
                    shangmi_activelog AS log 
                ON 
                    m.id=log.active_map_id 
                LEFT JOIN 
                    shangmi_active AS active 
                ON 
                    m.active_id=active.id 
                LEFT JOIN 
                    shangmi_saler AS saler
                ON
                    saler.id=log.saler_id
                LEFT JOIN
                    shangmi_customergetpricelog as plog
                ON
                    log.customer_get_price_log_id=plog.id
                LEFT JOIN 
                    shangmi_user AS u
                ON
                    plog.customer_id=u.id
                WHERE 
                    m.store_id={store_id}
                AND 
                    active.status=1  
                AND 
                    log.is_writeoff=FALSE
                AND 
                    log.time::date='{date}'
                AND 
                    plog.is_writeoff=TRUE;
            """.format(store_id=store_id, date=today)
    elif data_type == 'all':
        sql = """
                SELECT 
                    m.store_id, 
                    m.active_id, 
                    u.phone,
                    to_char(log.time, 'YYYY-MM-DD HH24:MI:SS') AS time,
                    active.name AS active_name,
                    saler.name AS saler_name,
                    plog.price AS price_sum,
                    saler.is_boss
                FROM 
                    shangmi_activestoremap AS m 
                LEFT JOIN 
                    shangmi_activelog AS log 
                ON 
                    m.id=log.active_map_id 
                LEFT JOIN 
                    shangmi_active AS active 
                ON 
                    m.active_id=active.id 
                LEFT JOIN 
                    shangmi_saler AS saler
                ON
                    saler.id=log.saler_id
                LEFT JOIN
                    shangmi_customergetpricelog as plog
                ON
                    log.customer_get_price_log_id=plog.id
                LEFT JOIN 
                    shangmi_user AS u
                ON
                    plog.customer_id=u.id
                WHERE 
                    m.store_id={store_id}
                AND 
                    active.status=1  
                AND 
                    plog.is_writeoff=TRUE
                AND 
                    log.is_writeoff=FALSE;
        """.format(store_id=store_id)
    elif data_type == 'history':
        sql = """
                SELECT 
                    m.store_id, 
                    m.active_id, 
                    u.phone,
                    to_char(log.time, 'YYYY-MM-DD HH24:MI:SS') AS time,
                    active.name AS active_name,
                    saler.name AS saler_name,
                    plog.price AS price_sum,
                    saler.is_boss
                FROM 
                    shangmi_activestoremap AS m 
                LEFT JOIN 
                    shangmi_activelog AS log 
                ON 
                    m.id=log.active_map_id 
                LEFT JOIN 
                    shangmi_active AS active 
                ON 
                    m.active_id=active.id 
                LEFT JOIN 
                    shangmi_saler AS saler
                ON
                    saler.id=log.saler_id
                LEFT JOIN
                    shangmi_customergetpricelog as plog
                ON
                    log.customer_get_price_log_id=plog.id
                LEFT JOIN 
                    shangmi_user AS u
                ON
                    plog.customer_id=u.id
                WHERE 
                    m.store_id={store_id}
                AND 
                    active.status=1  
                AND 
                    log.is_writeoff=TRUE
                AND 
                    plog.is_writeoff=TRUE
            ;
        """.format(store_id=store_id)
    else:
        return []
    cur = connection.cursor()
    cur.execute(sql)
    item_detail_list = dictfetchall(cur)
    # distribute = models.StoreMoneyDistribution.objects.get(
    #     active_id=active_id)
    # for data in item_detail_list:
    #     if data.get('is_boss') == True:
    #         data['distribute'] = distribute.boss_money 
    #     else:
    #         data['distribute'] = distribute.boss_distribute_money
    #     data['phone'] = data['phone'][0:3]+ '****'+ data['phone'][7:]
    return item_detail_list

def get_saler_records_detail(store_id, saler_id):
    sql = """
        SELECT 
                m.store_id, 
                m.active_id, 
                log.customer_id,
                u.phone,
                active.name AS active_name,
                saler.name AS saler_name,
                saler.is_boss AS is_boss,
                to_char(log.time, 'YYYY-MM-DD HH24:MI:SS') AS time,
                plog.price AS price_sum
            FROM 
                shangmi_activestoremap AS m 
            LEFT JOIN 
                shangmi_activelog AS log 
            ON 
                m.id=log.active_map_id 
            LEFT JOIN 
                shangmi_active AS active 
            ON 
                m.active_id=active.id 
            LEFT JOIN 
                shangmi_saler AS saler
            ON
                saler.id=log.saler_id
            LEFT JOIN
                shangmi_customergetpricelog as plog
            ON
                log.customer_get_price_log_id=plog.id
            LEFT JOIN 
                shangmi_user AS u
            ON
                plog.customer_id=u.id
            WHERE 
                m.store_id={store_id}
            AND 
                active.status=1  
            AND
                saler.id={saler_id}
            AND 
                plog.is_writeoff=TRUE
            AND 
                log.is_writeoff=FALSE
            ORDER BY
                active.id;
    """.format(store_id=store_id, saler_id=saler_id)
    cur = connection.cursor()
    cur.execute(sql)
    active_list = dictfetchall(cur)
    # money_sum = 0
    # advance_sum = 0
    for i in active_list:
        active_id = int(i.get('active_id'))
        i['phone'] = i['phone'][0:3]+ '****'+ i['phone'][7:]
        distribute = models.StoreMoneyDistribution.objects.get(
        active_id=active_id)
        if i.get('is_boss') == True:
            i['distribute'] = distribute.boss_money  
        else:
            i['distribute'] = distribute.boss_distribute_money
    #     advance_sum += i['price_sum']
    return {'data': active_list}