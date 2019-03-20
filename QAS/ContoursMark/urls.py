# !/usr/bin/env python3
# -*- encoding: utf-8 -*-
# @author: condi
# @file: urls.py
# @time: 19-2-20 下午3:25

from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^marks/(?P<pk>\d+)/$', views.SCUMarkView.as_view()),  # 查询/新增/修改
    url(r'^marks/delete/(?P<pk>\d+)/$', views.DMarkView.as_view()),  # 删除一条细胞轮廓坐标记录
    url(r'^marks/references/(?P<pk>\d+)/$', views.CUReferenceView.as_view()),  # 设置/修改参考对象
    url(r'^regions/(?P<pk>\d+)/$', views.DRegionView.as_view()),  # 删除区域中的一条记录
]
