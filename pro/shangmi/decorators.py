from django.http import JsonResponse, QueryDict, HttpResponse
from django.core.cache import cache
from django.core import exceptions
import exceptions as _exceptions
from collections import OrderedDict
from django.core.paginator import EmptyPage
import django.db
import traceback
import utils
import json
from models import *
from functools import reduce, wraps

exceptions_dict = OrderedDict()

exceptions_dict[exceptions.ObjectDoesNotExist] = {'return_code': 3, 'status': 400}
exceptions_dict[_exceptions.MethodNotAllowed] = {'return_code': 4, 'status': 405}
exceptions_dict[exceptions.MultipleObjectsReturned] = {'return_code': 7, 'status': 400}
exceptions_dict[exceptions.FieldError] = {'return_code': 8, 'status': 400}
exceptions_dict[django.db.IntegrityError] = {'return_code': 9, 'status': 409}
exceptions_dict[EmptyPage] = {'return_code': 10, 'status': 204}

exceptions_dict[Exception] = {'return_code': 1, 'status': 500}


def standard_api(methods=('GET', 'POST')):

    def _decorator(func):
        def decorator(request, *args, **kwargs):
            try:
                if request.method not in methods:
                    raise _exceptions.MethodNotAllowed(request.method)
                result = func(request, *args, **kwargs)
                if result and type(result) != dict:
                    return result
                response = {'code': 0}
                response.update(result or {})
                _status = 200
                if response.get('status'):
                    _status = response.pop('status')
                response = JsonResponse(response, status=_status)
                return response
            except tuple(exceptions_dict.keys()) as e:
                print traceback.format_exc()
                if exceptions_dict.get(type(e)):
                    _status = exceptions_dict.get(type(e)).get('status')
                    code = exceptions_dict.get(type(e)).get('return_code')
                else:
                    _status = 500
                    code = 1
                message = unicode(e)
                return JsonResponse({'code': code, 'error_msg': message}, status=_status)
        return decorator
    return _decorator


def token_required(func):
    """
    Decorator to make a view only confirm validate token
    """
    @wraps(func)
    def decorator(request, *args, **kwargs):
        params = QueryDict(request.body)
        token = params.get('token')
        if not token:
            token = request.GET.get('token')
        openid = None

        if token:
            try:
                openid = utils.confirm_validate_token(token)
            except:
                return HttpResponse(json.dumps({'code':2, 'data':u'Token illegal'}),
                                             content_type = 'application/json')
            guide = ShareUser.objects.filter(openid=openid).count()
        if not openid or openid == '':
            return HttpResponse(json.dumps({'code':2, 'data':u'Token illegal'}),
                                             content_type = 'application/json')
        return func(request, *args, **kwargs)

    return decorator


