# !/usr/bin/env python3
# -*- encoding: utf-8 -*-
# @author: condi
# @file: serializers.py
# @time: 19-2-20 下午4:32

from rest_framework import serializers
from .models import Patient


class PatientSerializer(serializers.ModelSerializer):
    """查增"""
    report_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S')
    send_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S')

    class Meta:
        model = Patient
        fields = ('id', 'name', 'age', 'gender', 'specimen_source',
                  'num_no', 'report_time', 'send_time')
