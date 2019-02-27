# !/usr/bin/env python3
# -*- encoding: utf-8 -*-
# @author: condi
# @file: urls.py
# @time: 19-2-25 上午10:02

from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^cases/(?P<pk>\d+)/$', views.SUDCaseView.as_view()),  # 查询/修改/删除
]
