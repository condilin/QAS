# !/usr/bin/env python3
# -*- encoding: utf-8 -*-
# @author: condi
# @file: urls.py
# @time: 19-2-20 下午3:21

from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^images/(?P<pk>\d+)/$', views.SUDImageView.as_view()),  # 查询/修改/删除
    url(r'^images/statistics/(?P<pk>\d+)/$', views.StatisticImageView.as_view()),  # 大图统计信息
    url(r'^images/add/$', views.CImageView.as_view()),  # 新增一条记录
    url(r'^images/$', views.SImageView.as_view()),  # 查询列表
]
