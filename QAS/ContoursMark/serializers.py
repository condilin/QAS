# !/usr/bin/env python3
# -*- encoding: utf-8 -*-
# @author: condi
# @file: serializers.py
# @time: 19-2-20 下午4:32

from rest_framework import serializers
from .models import RegionCoord, ContoursMark
# from Image.serializers import SCImageSerializer
#
#
# class RegionCoordSerializer(serializers.ModelSerializer):
#     """查增"""
#     image = serializers.IntegerField(write_only=True)
#
#     class Meta:
#         model = RegionCoord
#         fields = ('id', 'image', 'x', 'y', 'w', 'h')
#
#
# class ContoursMarkSerializer(serializers.ModelSerializer):
#     """查增"""
#     image = serializers.IntegerField(write_only=True)
#     region = RegionCoordSerializer(many=True, read_only=True)
#
#     class Meta:
#         model = ContoursMark
#         fields = ('id', 'image', 'region')
