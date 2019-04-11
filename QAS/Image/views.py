from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView

import os
import time
import numpy as np
from QAS.settings.dev import DATA_SAMBA_PREX

from Image.models import Image
from Image.serializers import SCUImageSerializer

import logging
logger = logging.getLogger('qas')


class StatisticImageView(APIView):
    """
    大图中的标注报告
    """

    def get(self, request, pk):

        # 根据id, 查询数据库
        try:
            image = Image.objects.get(id=pk, is_delete=False)
        except Image.DoesNotExist as e:
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR, data={'msg': '数据不存在！'})

        # 定义返回结果列表
        result_dict = {}

        # ---------- 统计该大图下参考对象的平均灰度值 ---------- #
        # 定义列表存储所有参考对象的灰度值
        gray_value_list = []
        # 查询该大图所有的参考对象
        all_reference = image.regions.filter(is_reference_obj=True)
        # 判断该大图是否有参考对象
        if all_reference:
            # 循环所有参考对象, 将灰度值添加到列表
            for obj in all_reference:
                gray_value_list.extend(obj.contours.values_list('cells_contours_gray', flat=True))
            # 计算灰度值平均值
            gray_avg = round(np.average(gray_value_list), 2)
            # 添加到结果列表
            result_dict['gray_avg'] = gray_avg
        else:
            result_dict['gray_avg'] = None
            # 没有参考对象的话, 不再进行后缀的计算, 直接返回
            return Response(status=status.HTTP_200_OK, data={'result_dict': result_dict})

        # ---------- 统计非参考对象的信息：标注区域id, 灰度值, 面积, di值, 细胞轮廓数量 ---------- #
        # 定义列表存储所有非参考对象的信息
        info_list = []
        # 查询该大图所有的标注框
        all_no_reference = image.regions.filter(is_reference_obj=False)
        # 判断该大图是否有标注对象
        if all_no_reference:
            # 循环所有标注对象
            for obj in all_no_reference:
                # 获取每个标注区域中所有轮廓的灰度值和面积字典
                contour_info = obj.contours.values('id', 'cells_contours_gray', 'cells_contours_area')
                # 如果只有框选区域, 没有细胞核的话, 该区域会被跳过
                if contour_info:
                    # 标注区域中的细胞核数量
                    cells_count = contour_info.count()
                    # 如果有标注区域中有多个轮廓, 则计算该轮廓的平均灰度值和平均面积
                    if cells_count > 1:
                        cells_contours_area = np.sum([i['cells_contours_area'] for i in contour_info]) / cells_count
                        cells_contours_gray = np.sum([i['cells_contours_gray'] for i in contour_info]) / cells_count
                    else:
                        cells_contours_area = contour_info[0]['cells_contours_area']
                        cells_contours_gray = contour_info[0]['cells_contours_gray']
                    # 计算标注区域的di值
                    cell_region_di = round(cells_contours_gray / result_dict['gray_avg'], 2)
                    # 获取标注区域id
                    region_id = obj.id

                    info_list.append({
                        'cells_contours_area': cells_contours_area,
                        'cells_contours_gray': cells_contours_gray,
                        'cell_region_di': cell_region_di,
                        'cells_count': cells_count,
                        'region_id': region_id
                    })
                else:
                    # 没有细胞核的区域会被跳过
                    continue

        # 将标注区域信息添加到最后返回结果中
        result_dict['info_list'] = info_list

        return Response(status=status.HTTP_200_OK, data={'result_dict': result_dict})


class SImageView(ListAPIView):
    """
    get: 查询大图列表
    """

    # 指定查询集, 获取没有逻辑删除的数据
    queryset = Image.objects.filter(is_delete=False).order_by('-last_open_time')

    # 指定序列化器
    serializer_class = SCUImageSerializer


class CImageView(APIView):
    """
    post: 新增一条记录
    """

    def post(self, request):

        # 获取图片路径
        full_path = request.data.get('full_storage_path', None)
        if not full_path:
            return Response(status=status.HTTP_400_BAD_REQUEST, data="请输入要打开的路径！")

        # 对图像路径进行处理
        full_path = full_path.replace('\\', '/').replace('//192.168.2.221/', '')
        full_path = DATA_SAMBA_PREX + full_path

        # 获取存储路径, 文件名, 后缀
        storage_path = os.path.dirname(full_path)
        file_name, suffix = os.path.splitext(os.path.basename(full_path))
        if not file_name:
            return Response(status=status.HTTP_400_BAD_REQUEST, data="请输入要打开的文件名！")
        if suffix not in ['.kfb', '.TMAP', '.tif']:
            return Response(status=status.HTTP_400_BAD_REQUEST, data="文件后缀仅支持kfb,TMAP,tif类型！")

        # 判断该文件是否已存在于数据库中, 不存在则新增一条记录
        image_select = Image.objects.filter(
            file_name=file_name, suffix=suffix,
            storage_path=storage_path, is_delete=False
        )
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
            serialize = SCUImageSerializer(image)
            return Response(status=status.HTTP_201_CREATED, data={'result': serialize.data})


class CPONImageView(APIView):
    """
    post: 新增前一条或后一条大图记录
    """

    def post(self, request):

        # 获取当前大图的id
        current_image_id = request.data.get('current_image_id', None)
        if not current_image_id:
            return Response(status=status.HTTP_400_BAD_REQUEST, data="请输入正确的参数！")

        # 获取上一张或下一张大图的标志
        previous_or_next_flag = request.data.get('previous_or_next_flag', None)
        if previous_or_next_flag not in ['previous', 'next']:
            return Response(status=status.HTTP_400_BAD_REQUEST, data="请输入正确的参数！")

        # 根据当前大图id, 查询出当前大图所在的文件夹路径
        try:
            current_img = Image.objects.get(id=current_image_id, is_delete=False)
        except Image.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND, data={'msg': '数据不存在！'})
        # 根据当前文件夹的路径, 查询该文件夹中的所有其它的大图
        all_img_list = os.listdir(current_img.storage_path)
        # 筛选符合后缀的文件名(kfb/TMAP/tif)
        filter_img_list = [img for img in all_img_list if img.endswith(('.kfb', '.TMAP', '.tif'))]
        # 对文件名进行排序
        filter_img_list.sort()

        # 获取当前大图所在符合筛选条件列表中的位置
        current_img_index = filter_img_list.index(current_img.file_name+current_img.suffix)

        # 保存当前大寿图的上一张大图
        if previous_or_next_flag == 'previous':
            # 如果索引为第一张, 则没有前一张
            if current_img_index == 0:
                return Response(status=status.HTTP_200_OK, data={'result': {'id': None}})
            else:
                # 有前一张, 则保存该大图路径到数据库
                previous_img_name = filter_img_list[current_img_index - 1]

                # 获取前一张大图的文件名/后缀/全路径
                file_name, suffix = os.path.splitext(previous_img_name)
                full_path = os.path.join(current_img.storage_path, previous_img_name)

        else:
            # 如果索引为最后一张, 则没有后一张
            if current_img_index == (len(filter_img_list) - 1):
                return Response(status=status.HTTP_200_OK, data={'result': {'id': None}})
            else:
                # 有后一张, 则保存该大图路径到数据库
                next_img_name = filter_img_list[current_img_index + 1]

                # 获取后一张大图的文件名/后缀/全路径
                file_name, suffix = os.path.splitext(next_img_name)
                full_path = os.path.join(current_img.storage_path, next_img_name)

        # 判断该文件是否已存在于数据库中, 不存在则新增一条记录
        image_select = Image.objects.filter(
            file_name=file_name, suffix=suffix,
            storage_path=current_img.storage_path, is_delete=False
        )
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
            try:
                previous_or_next_obj = Image.objects.create(
                    file_name=file_name, suffix=suffix, file_size=file_size,
                    storage_path=current_img.storage_path, last_open_time=last_open_time
                )
            except Exception as e:
                logger.error('qas创建前/后一条记录出错！')
                return Response(
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR, data={'msg': '数据库新增记录出错！'}
                )

            # 序列化返回
            ser = SCUImageSerializer(previous_or_next_obj)
            return Response(status=status.HTTP_201_CREATED, data={'result': ser.data})


class SUDImageView(APIView):
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
        serializer = SCUImageSerializer(image)
        return Response(serializer.data)

    def patch(self, request, pk):

        # 获取最新的文件打开时间
        lastest_open_time = request.data.get('last_open_time', None)

        if not lastest_open_time:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={'msg': '请输入正确的参数！'})

        # 根据大图id, 查询数据库对象
        try:
            image = Image.objects.get(id=pk, is_delete=False)
        except Image.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND, data={'msg': '数据不存在！'})

        # 更新文件打开时间
        image.last_open_time = lastest_open_time
        image.save()

        # 序列化返回
        serializer = SCUImageSerializer(image)
        return Response(serializer.data)

    def delete(self, request, pk):
        # 根据id, 查询数据库对象
        try:
            image = Image.objects.get(id=pk, is_delete=False)
        except Image.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND, data={'msg': '数据不存在！'})

        try:
            # 数据库物理删除
            image.delete()
        except Exception as e:
            logger.warning(e)
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR, data={'msg': '数据库删除失败！'})

        return Response(status=status.HTTP_204_NO_CONTENT, data={'msg': '删除成功！'})
