# !/usr/bin/env python3
# -*- encoding: utf-8 -*-
# @author: condi
# @file: serializers.py
# @time: 19-2-20 下午4:32

from rest_framework import serializers
from .models import Patient


class SCPatientSerializer(serializers.ModelSerializer):
    """查增"""
    report_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S')
    send_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S')
    name = serializers.CharField(read_only=True)
    # age = serializers.CharField(read_only=True)
    specimen_source = serializers.CharField(read_only=True)
    num_no = serializers.CharField(read_only=True)
    diagnose_label = serializers.CharField(read_only=True)

    class Meta:
        model = Patient
        fields = ('id', 'name', 'age', 'gender', 'specimen_source',
                  'num_no', 'report_time', 'send_time', 'diagnose_label')

    def validate_age(self, value):

        """验证年龄"""
        if value:
            if int(value) > 100 or int(value) < 10:
                raise serializers.ValidationError('参数错误')
        return value


class UPatientSerializer(serializers.ModelSerializer):
    """修改"""
    report_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    send_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    name = serializers.CharField(read_only=True)
    # age = serializers.CharField(read_only=True)
    specimen_source = serializers.CharField(read_only=True)
    num_no = serializers.CharField(read_only=True)
    diagnose_label = serializers.CharField(read_only=True)

    class Meta:
        model = Patient
        fields = ('id', 'name', 'age', 'gender', 'specimen_source',
                  'num_no', 'report_time', 'send_time', 'diagnose_label')

    def validate_age(self, value):

        """验证年龄"""
        if value:
            if int(value) > 100 or int(value) < 10:
                raise serializers.ValidationError('参数错误')
        return value
