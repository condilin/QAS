from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, ListCreateAPIView
from django.forms.models import model_to_dict

import numpy as np

from ContoursMark.models import RegionCoord, ContoursMark
from Image.models import Image

import logging
logger = logging.getLogger('qas')


class SCUDMarkView(APIView):
    """
    get: 查询一张大图中所有的细胞轮廓坐标列表
    post: 新增一条细胞轮廓坐标记录
    patch: 修改一条细胞轮廓坐标记录
    delete: 物理删除一条细胞轮廓坐标记录
    """

    def get(self, request, img_id):

        # 根据大图id, 查询数据库对象
        try:
            # 获取大图没有逻辑删除的数据
            image = Image.objects.get(id=img_id, is_delete=False)
        except Image.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND, data={'msg': '数据不存在！'})

        # ---------- 定义返回所有区域的结果列表 ---------- #
        result_dict = {'id': img_id, 'result': []}

        # ---------- 返回该大图下参考对象的平均灰度值 ---------- #
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

        # ---------- 返回该大图所有的区域及轮廓信息 ---------- #
        # 通过外键返回该大图的所有区域
        regions_list = image.regions.all()
        # 循环所有区域
        for mark in regions_list:
            # 定义保存一个区域的结果字典
            result_dict_tmp = {}

            # 将queryset转换成dict类型
            region_obj = model_to_dict(mark)
            result_dict_tmp['x'] = region_obj['x']
            result_dict_tmp['y'] = region_obj['y']
            result_dict_tmp['w'] = region_obj['w']
            result_dict_tmp['h'] = region_obj['h']
            result_dict_tmp['is_reference_obj'] = region_obj['is_reference_obj']
            result_dict_tmp['region_id'] = region_obj['id']

            # 通过外键返回该区域中的所有轮廓
            mark_list = mark.contours.all()
            # 定义细胞核量化信息的字典
            contours_info = []
            # 循环所有轮廓
            for cts in mark_list:
                # 将queryset转换成dict类型
                cts_dict = model_to_dict(cts)
                # 细胞核量化信息的列表
                contours_info.append(
                    {
                        # 使用eval将字符串列表'[[1,2,3]]', 转换成列表[1,2,3]
                        'cells_contours_coord': eval(cts_dict['cells_contours_coord']),
                        'cells_contours_area': cts_dict['cells_contours_area'],
                        'cells_contours_perimeter': cts_dict['cells_contours_perimeter'],
                        'cells_contours_gray': cts_dict['cells_contours_gray'],
                        'contours_id': cts_dict['id']
                    }
                )
            # 保存一个区域的所有信息
            result_dict_tmp['contours_info'] = contours_info
            # 保存所有区域的所有信息
            result_dict['result'].append(result_dict_tmp)

        return Response(status=status.HTTP_200_OK, data=result_dict)

    def post(self, request, img_id):

        # 获取请求体中的表单数据并在RegionCoord表创建记录
        region_obj = RegionCoord.objects.create(
            image=Image.objects.get(id=img_id),
            is_reference_obj=request.data['is_reference_obj'],
            x=request.data['x'], y=request.data['y'], w=request.data['w'], h=request.data['h']
        )

        # ContoursMark表创建记录
        # 可能有有多个标记轮廓, 需要循环创建记录
        contours_info = request.data['contours_info']
        for contour in contours_info:
            contour_obj = ContoursMark.objects.create(
                # 获取RegionCoord表创建的记录
                region=region_obj,
                cells_contours_coord=contour['cells_contours_coord'],
                cells_contours_area=contour['cells_contours_area'],
                cells_contours_perimeter=contour['cells_contours_perimeter'],
                cells_contours_gray=contour['cells_contours_gray'],
            )

            # 将大图id, 区域坐标id, 轮廓id(自身的id)一起返回
            contour['img_id'] = img_id
            contour['region_id'] = region_obj.id
            contour['contours_id'] = contour_obj.id

        return Response(status=status.HTTP_201_CREATED, data=contours_info)

    def patch(self, request, img_id):

        # 获取轮廓id,区域id以及是否做为参考对象
        contours_id = request.data.get('contours_id', None)
        region_id = request.data.get('region_id', None)

        if not contours_id and not region_id:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={'msg': '请输入正确的参数！'})

        if contours_id and region_id:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={'msg': '确定修改的是contours还是region！'})

        # ------------------------- 修改区域数据 ------------------------- #
        # 修改区域(需要传区域id, 根据区域id查询出所有的轮廓id, 并删除这些轮廓, 因为修改了原区域之后, 新的区域
        # 又会识别出不同的轮廓, 之前的轮廓已经没用了, 然后再新增新轮廓到数据库中)
        if region_id:
            # 根据区域id, 查询数据库对象
            try:
                region = RegionCoord.objects.get(id=region_id, is_delete=False)
            except RegionCoord.DoesNotExist:
                return Response(status=status.HTTP_404_NOT_FOUND, data={'msg': '数据不存在！'})

            # 获取用户所选区域数据
            # is_reference_obj = request.data['is_reference_obj'],
            x, y, w, h = request.data['x'], request.data['y'], request.data['w'], request.data['h']

            # 修改并保存数据
            region.x = x
            region.y = y
            region.w = w
            region.h = h
            # region.is_reference_obj = is_reference_obj
            region.save()

            # 删除该区域中原来识别的轮廓
            region.contours.filter(is_delete=False).delete()

            # 增加新的轮廓点
            # ContoursMark表创建记录
            # 可能没有标记点, 也可能有有多个标记轮廓, 如果是多个, 则需要循环创建记录
            contours_info = request.data.get('contours_info', None)
            for contour in contours_info:
                contour_obj = ContoursMark.objects.create(
                    # 获取RegionCoord表已修改的记录
                    region=region,
                    cells_contours_coord=contour['cells_contours_coord'],
                    cells_contours_area=contour['cells_contours_area'],
                    cells_contours_perimeter=contour['cells_contours_perimeter'],
                    cells_contours_gray=contour['cells_contours_gray'],
                )
                # 将大图id, 区域坐标id, 轮廓id(自身的id)一起返回
                contour['img_id'] = img_id
                contour['region_id'] = region.id
                contour['contours_id'] = contour_obj.id

            return Response(status=status.HTTP_201_CREATED, data=contours_info)

        # ------------------------- 修改轮廓数据 ------------------------- #
        # 只修改轮廓(只传contours_id)
        if contours_id:
            # 根据轮廓id, 查询数据库对象
            try:
                contours = ContoursMark.objects.get(id=contours_id, is_delete=False)
            except ContoursMark.DoesNotExist:
                return Response(status=status.HTTP_404_NOT_FOUND, data={'msg': '数据不存在！'})

            # 获取细胞核轮廓数据
            contours_info = request.data['contours_info'][0]
            cells_contours_coord = contours_info['cells_contours_coord']
            cells_contours_area = contours_info['cells_contours_area']
            cells_contours_perimeter = contours_info['cells_contours_perimeter']
            cells_contours_gray = contours_info['cells_contours_gray']

            # 修改并保存数据
            contours.cells_contours_coord = cells_contours_coord
            contours.cells_contours_area = cells_contours_area
            contours.cells_contours_perimeter = cells_contours_perimeter
            contours.cells_contours_gray = cells_contours_gray
            contours.save()

            # 返回修改后的数据
            res_to_dict = model_to_dict(contours)
            res = {
                'contours_info': [{
                    'cells_contours_coord': res_to_dict['cells_contours_coord'],
                    'cells_contours_area': res_to_dict['cells_contours_area'],
                    'cells_contours_perimeter': res_to_dict['cells_contours_perimeter'],
                    'cells_contours_gray': res_to_dict['cells_contours_gray']
                }],
                'contours_id': res_to_dict['id']
            }
            return Response(status=status.HTTP_200_OK, data=res)

    def delete(self, request, img_id):

        # ------------------------- 删除整张大图数据 ------------------------- #
        # 根据大图id, 查询数据库对象
        try:
            image = Image.objects.get(id=img_id, is_delete=False)
        except Image.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND, data={'msg': '数据不存在！'})

        # 获取区域id和轮廓id
        region_id = request.data.get('region_id', None)
        contours_id = request.data.get('contours_id', None)

        # 如果没有带region_id和region_id, 则说明要删除整张大图
        if not region_id and not contours_id:
            try:
                # 数据库中物理删除, 同时级联删除其它外键关联
                # image.delete()
                image.is_delete = True
                image.save()
            except Exception as e:
                logger.warning(e)
                return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR, data={'msg': '数据库删除失败！'})

            return Response(status=status.HTTP_204_NO_CONTENT, data={'msg': '删除整张大图成功！'})

        # ------------------------- 删除区域数据或轮廓数据 ------------------------- #
        # 如果带上region_id和region_id其中一个, 则对应删除其中一个
        if region_id:
            # 根据区域id, 查询数据库对象
            try:
                region = RegionCoord.objects.get(id=region_id, is_delete=False)
            except RegionCoord.DoesNotExist:
                return Response(status=status.HTTP_404_NOT_FOUND, data={'msg': '数据不存在！'})

            try:
                # 数据库中物理删除, 同时级联删除其它外键关联
                region.delete()
            except Exception as e:
                logger.warning(e)
                return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR, data={'msg': '数据库删除失败！'})

            return Response(status=status.HTTP_204_NO_CONTENT, data={'msg': '删除整个区域成功！'})

        else:
            # 根据轮廓id, 查询数据库对象
            try:
                contours = ContoursMark.objects.get(id=contours_id, is_delete=False)
            except ContoursMark.DoesNotExist:
                return Response(status=status.HTTP_404_NOT_FOUND, data={'msg': '数据不存在！'})

            try:
                # 数据库中物理删除
                contours.delete()
            except Exception as e:
                logger.warning(e)
                return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR, data={'msg': '数据库删除失败！'})

            return Response(status=status.HTTP_204_NO_CONTENT, data={'msg': '删除细胞核轮廓成功！'})


class CUReferenceView(APIView):
    """
    patch: 修改是否为参考对象
    """

    def patch(self, request, region_id):

        # 获取参考对象设置值
        is_reference_obj = request.data.get('is_reference_obj', None)

        if not is_reference_obj:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={'msg': '请输入正确的参数！'})

        # 根据轮廓id, 查询数据库对象
        try:
            region = RegionCoord.objects.get(id=region_id, is_delete=False)
        except ContoursMark.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND, data={'msg': '数据不存在！'})

        # 修改是否为参考对象
        region.is_reference_obj = is_reference_obj
        region.save()

        return Response(status=status.HTTP_200_OK, data={
            'region_id': region_id, 'is_reference_obj': is_reference_obj
        })