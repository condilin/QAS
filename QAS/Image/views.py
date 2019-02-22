from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, ListCreateAPIView

import os
import time
import json
from QAS.settings.dev import DATA_SAMBA_PREX

from Image.models import Image
from Image.serializers import SCImageSerializer

import logging
logger = logging.getLogger('qas')


class SImageView(ListAPIView):
    """
    get: 查询大图列表
    """

    # 指定查询集, 获取没有逻辑删除的数据, 返回最近打开的前6条记录
    queryset = Image.objects.filter(is_delete=False).order_by('-last_open_time')[:10]

    # 指定序列化器
    serializer_class = SCImageSerializer


class CImageView(APIView):
    """
    post: 新增一条记录
    """

    def post(self, request):

        # 获取图片路径
        full_path = request.data.get('full_storage_path', None)
        if not full_path:
            return Response(status=status.HTTP_400_BAD_REQUEST, data="请输入要打开的路径！")
        full_path = DATA_SAMBA_PREX + full_path

        # 获取存储路径, 文件名, 后缀
        storage_path = os.path.dirname(full_path)
        file_name, suffix = os.path.splitext(os.path.basename(full_path))
        if not file_name:
            return Response(status=status.HTTP_400_BAD_REQUEST, data="请输入要打开的文件名！")

        # 判断该文件是否已存在于数据库中, 不存在则新增一条记录
        image_select = Image.objects.filter(file_name=file_name, is_delete=False)
        print(image_select)
        if image_select:
            # 返回该大图的id
            return Response(status=status.HTTP_201_CREATED, data={'result': {'id': image_select[0].id}})

        else:
            # ---- 获取文件的size ---- #
            # 读取文件大小
            byte_size = os.path.getsize(full_path)
            m_size = round(byte_size / 1024 / 1024, 1)

            # ---- 获取文件大小 ----- #
            file_size = str(m_size) + 'M'

            # ---- 获取当前时间 ----- #
            last_open_time = time.strftime("%Y-%m-%d %H:%M:%S")

            # 创建记录
            image = Image.objects.create(
                file_name=file_name, suffix=suffix, file_size=file_size,
                storage_path=storage_path, last_open_time=last_open_time
            )

            # 序列化返回
            serialize = SCImageSerializer(image)
            return Response(status=status.HTTP_201_CREATED, data={'result': serialize.data})


class SDImageView(APIView):
    """
    get: 查询一条大图数据
    delete: 逻辑删除一条大图数据
    """

    def get(self, request, pk):
        # 根据id, 查询数据库对象
        try:
            image = Image.objects.get(id=pk, is_delete=False)
        except Image.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND, data={'msg': '数据不存在！'})

        # 序列化返回
        serializer = SCImageSerializer(image)
        return Response(serializer.data)

    def delete(self, request, pk):
        # 根据id, 查询数据库对象
        try:
            image = Image.objects.get(id=pk, is_delete=False)
        except Image.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND, data={'msg': '数据不存在！'})

        try:
            # 数据库中逻辑删除
            image.is_delete = True
            image.save()
        except Exception as e:
            logger.warning(e)
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR, data={'msg': '数据库删除失败！'})

        return Response(status=status.HTTP_204_NO_CONTENT, data={'msg': '删除成功！'})
