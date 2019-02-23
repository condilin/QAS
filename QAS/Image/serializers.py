# !/usr/bin/env python3
# -*- encoding: utf-8 -*-
# @author: condi
# @file: serializers.py
# @time: 19-2-20 下午4:32

from rest_framework import serializers
from .models import Image


class SCUImageSerializer(serializers.ModelSerializer):
    """查增修"""
    last_open_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = Image
        fields = ('id', 'file_name', 'suffix', 'storage_path', 'last_open_time', 'file_size')
