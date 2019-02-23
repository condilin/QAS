# !/usr/bin/env python3
# -*- encoding: utf-8 -*-
# @author: condi
# @file: urls.py
# @time: 19-2-20 下午3:25

from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^marks/references/(?P<region_id>\d+)/$', views.CUReferenceView.as_view()),  # 设置/修改参考对象
    url(r'^marks/(?P<img_id>\d+)/$', views.SCUDMarkView.as_view()),  # 查询/新增/修改/删除一条记录
]