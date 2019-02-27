# !/usr/bin/env python3
# -*- encoding: utf-8 -*-
# @author: condi
# @file: urls.py
# @time: 19-2-24 下午8:49

from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^patients/(?P<pk>\d+)/$', views.SCUDPatientView.as_view()),  # 查询/新增/修改/删除一条记录
]
