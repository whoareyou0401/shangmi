import requests
import json
from PIL import Image
from io import BytesIO

def get_access_token():
	params = {'appid': 'wx8b50ab8fa813a49e',
			  'secret': 'b32f63c36ea123710173c4c9d4b15e8b',
			  'grant_type': 'client_credential'}
	url = 'https://api.weixin.qq.com/cgi-bin/token'
	response = requests.get(url, params=params)
	res = json.loads(response.content)
	return res.get('access_token')


def get_qrcode(wx_path):
	token = get_access_token()
	# url = "https://api.weixin.qq.com/wxa/getwxacode?access_token=%s" % token
	url = "https://api.weixin.qq.com/cgi-bin/wxaapp/createwxaqrcode?access_token=%s" % token
	# params = {
	# 	'path': 'pages/bind_phone/bind_phone?store_id=%s&active_id=%s' % (store_id, active_id),
	# 	'width': 430,
	# 	'auto_color': True,
	# 	'line_color': {"r":"0","g":"0","b":"0"}
	# }
	params = {
		'path': wx_path,
		'width': 430,
	}
	response = requests.post(url, data=json.dumps(params))
	# img = Image.open(BytesIO(response.content))
	# img.save(save_path)
	return response.content

# get_qrcode('3', '1')
img = Image.open('/home/liuda/django_project/shangmi/store3active1.png')