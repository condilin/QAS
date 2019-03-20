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
    delete: 删除一条细胞轮廓坐标记录
    """

    def get(self, request, pk):

        # 根据大图id, 查询数据库对象
        try:
            # 获取大图没有逻辑删除的数据
            image = Image.objects.get(id=pk, is_delete=False)
        except Image.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND, data={'msg': '数据不存在！'})

        # ---------- 定义返回所有区域的结果列表 ---------- #
        result_dict = {'id': pk, 'result': []}

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

    def post(self, request, pk):

        # 先判断flag修改的是框选区域还是轮廓
        flag = request.data.get('flag')

        # 获取轮廓id,区域id以及是否做为参考对象
        if flag == 'region':
            # ------------------------- 新增区域数据 ------------------------- #
            # 如何有获取到传来的region_id, 说明是在区域里面添加细胞核, 否则是在区域外面添加
            new_region_id = request.data.get('region_id', None)
            if new_region_id:
                try:
                    region_obj = RegionCoord.objects.get(id=new_region_id)
                except RegionCoord.DoesNotExist:
                    return Response(status=status.HTTP_404_NOT_FOUND, data={'msg': '数据不存在！'})
            else:
                # 获取请求体中的表单数据并在RegionCoord表创建记录
                region_obj = RegionCoord.objects.create(
                    image=Image.objects.get(id=pk),
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

                # 将大图id, 区域坐标id, 轮廓id(自身的id), 是否为参考对象一起返回
                contour['img_id'] = pk
                contour['region_id'] = region_obj.id
                contour['contours_id'] = contour_obj.id
                contour['is_reference_obj'] = request.data['is_reference_obj']

            # ----- 返回参考对象最新的灰度平均值 ------ #
            if request.data['is_reference_obj'] == 1:
                # 定义列表存储所有参考对象的灰度值
                gray_value_list = []
                # 直接查询该大图所有的参考对象
                all_reference = Image.objects.get(id=pk).regions.filter(is_reference_obj=True)
                # 判断该大图是否有参考对象
                if all_reference:
                    # 循环所有参考对象, 将灰度值添加到列表
                    for obj in all_reference:
                        gray_value_list.extend(obj.contours.values_list('cells_contours_gray', flat=True))
                    # 计算灰度值平均值
                    gray_avg = round(np.average(gray_value_list), 2)
                else:
                    gray_avg = None
            else:
                gray_avg = None

            # 最终返回结果
            return Response(status=status.HTTP_201_CREATED,
                            data={'contours_info': contours_info, 'gray_avg': gray_avg})

        elif flag == 'contours':
            # ------------------------- 新增轮廓数据 ------------------------- #
            # 新增轮廓(传contours_id以及在哪个region中添加, 同时判断是否为参考对象,是则更新平均灰度值)
            # 将x-www-form-urlencoded类型并转换成dict类型
            region_id = request.data.dict().get('region_id', None)
            is_reference_obj = request.data.dict().get('is_reference_obj', None)
            if not region_id or not is_reference_obj:
                return Response(status=status.HTTP_400_BAD_REQUEST, data={'msg': '请输入正确的参数！'})

            # 查询出要添加轮廓的区域
            try:
                region = RegionCoord.objects.get(id=region_id, is_delete=False)
            except RegionCoord.DoesNotExist:
                return Response(status=status.HTTP_404_NOT_FOUND, data={'msg': '数据不存在！'})

            # 获取细胞核轮廓数据, 并将x-www-form-urlencoded类型并转换成dict类型
            contours_info = request.data.dict()
            contour_obj = ContoursMark.objects.create(
                # 获取RegionCoord表创建的记录
                region=region,
                cells_contours_coord=eval(contours_info['cells_contours_coord']),
                cells_contours_area=contours_info['cells_contours_area'],
                cells_contours_perimeter=contours_info['cells_contours_perimeter'],
                cells_contours_gray=contours_info['cells_contours_gray'],
            )

            # ----- 返回参考对象最新的灰度平均值 ------ #
            # 因为此接口使用了x-www-form的数据类型, 因此获取的参数全部会变成字符串
            if is_reference_obj == 'true' or is_reference_obj == '1' or is_reference_obj == 1:
                # 定义列表存储所有参考对象的灰度值
                gray_value_list = []
                # 直接查询该大图所有的参考对象
                all_reference = Image.objects.get(id=pk).regions.filter(is_reference_obj=True)
                # 判断该大图是否有参考对象
                if all_reference:
                    # 循环所有参考对象, 将灰度值添加到列表
                    for obj in all_reference:
                        gray_value_list.extend(obj.contours.values_list('cells_contours_gray', flat=True))
                    # 计算灰度值平均值
                    gray_avg = round(np.average(gray_value_list), 2)
                else:
                    gray_avg = None
            else:
                gray_avg = None

            # 返回新增后的数据
            res_to_dict = model_to_dict(contour_obj)
            res = {
                'contours_info': [{
                    'cells_contours_coord': res_to_dict['cells_contours_coord'],
                    'cells_contours_area': res_to_dict['cells_contours_area'],
                    'cells_contours_perimeter': res_to_dict['cells_contours_perimeter'],
                    'cells_contours_gray': res_to_dict['cells_contours_gray']
                }],
                'contours_id': res_to_dict['id'],
                'region_id': contour_obj.region.id,
                'gray_avg': gray_avg
            }
            return Response(status=status.HTTP_200_OK, data=res)

        else:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={'msg': '请输入正确的参数！'})

    def patch(self, request, pk):

        # 先判断flag修改的是框选区域还是轮廓
        flag = request.data.get('flag')

        # 获取轮廓id,区域id以及是否做为参考对象
        if flag == 'contours':
            # ------------------------- 修改轮廓数据 ------------------------- #
            # 只修改轮廓(只传contours_id,同时判断是否为参考对象,是则更新平均灰度值)
            # 将x-www-form-urlencoded类型并转换成dict类型
            contours_id = request.data.dict().get('contours_id', None)
            is_reference_obj = request.data.dict().get('is_reference_obj', None)
            if not contours_id or not is_reference_obj:
                return Response(status=status.HTTP_400_BAD_REQUEST, data={'msg': '请输入正确的参数！'})

            # 根据轮廓id, 查询数据库对象
            try:
                contours = ContoursMark.objects.get(id=contours_id, is_delete=False)
            except ContoursMark.DoesNotExist:
                return Response(status=status.HTTP_404_NOT_FOUND, data={'msg': '数据不存在！'})

            # 获取细胞核轮廓数据, 并将x-www-form-urlencoded类型并转换成dict类型
            contours_info = request.data.dict()
            # 获取细胞轮廓坐标
            cells_contours_coord = eval(contours_info['cells_contours_coord'])
            cells_contours_area = contours_info['cells_contours_area']
            cells_contours_perimeter = contours_info['cells_contours_perimeter']
            cells_contours_gray = contours_info['cells_contours_gray']

            # 修改并保存数据
            contours.cells_contours_coord = cells_contours_coord
            contours.cells_contours_area = cells_contours_area
            contours.cells_contours_perimeter = cells_contours_perimeter
            contours.cells_contours_gray = cells_contours_gray
            contours.save()

            # ----- 返回参考对象最新的灰度平均值 ------ #
            # 因为此接口使用了x-www-form的数据类型, 因此获取的参数全部会变成字符串
            if is_reference_obj == 'true' or is_reference_obj == '1' or is_reference_obj == 1:
                # 定义列表存储所有参考对象的灰度值
                gray_value_list = []
                # 直接查询该大图所有的参考对象
                all_reference = Image.objects.get(id=pk).regions.filter(is_reference_obj=True)
                # 判断该大图是否有参考对象
                if all_reference:
                    # 循环所有参考对象, 将灰度值添加到列表
                    for obj in all_reference:
                        gray_value_list.extend(obj.contours.values_list('cells_contours_gray', flat=True))
                    # 计算灰度值平均值
                    gray_avg = round(np.average(gray_value_list), 2)
                else:
                    gray_avg = None
            else:
                gray_avg = None

            # 返回修改后的数据
            res_to_dict = model_to_dict(contours)
            res = {
                'contours_info': [{
                    'cells_contours_coord': res_to_dict['cells_contours_coord'],
                    'cells_contours_area': res_to_dict['cells_contours_area'],
                    'cells_contours_perimeter': res_to_dict['cells_contours_perimeter'],
                    'cells_contours_gray': res_to_dict['cells_contours_gray']
                }],
                'contours_id': res_to_dict['id'],
                'gray_avg': gray_avg
            }
            return Response(status=status.HTTP_200_OK, data=res)

        elif flag == 'region':
            # ------------------------- 修改区域数据 ------------------------- #
            # 修改区域(需要传区域id, 根据区域id查询出所有的轮廓id, 并删除这些轮廓, 因为修改了原区域之后, 新的区域
            # 又会识别出不同的轮廓, 之前的轮廓已经没用了, 然后再新增新轮廓到数据库中)

            region_id = request.data.get('region_id', None)
            if not region_id:
                return Response(status=status.HTTP_400_BAD_REQUEST, data={'msg': '请输入正确的参数！'})

            # 根据区域id, 查询数据库对象
            try:
                region = RegionCoord.objects.get(id=region_id, is_delete=False)
            except RegionCoord.DoesNotExist:
                return Response(status=status.HTTP_404_NOT_FOUND, data={'msg': '数据不存在！'})

            # 获取用户所选区域数据
            try:
                x, y, w, h = request.data['x'], request.data['y'], request.data['w'], request.data['h']
            except Exception as e:
                return Response(status=status.HTTP_404_NOT_FOUND, data={'msg': '请输入正确的参数！'})

            # 不知为何使用request.data['is_reference_obj']获取到的数据是tuple类型:(0, ), 从而结果保存不到数据库
            # 而使用request.data.get('is_reference_obj', None), 则获取到的数据类型为int, 0
            is_reference_obj = request.data.get('is_reference_obj', None)

            # 修改并保存数据
            region.x = x
            region.y = y
            region.w = w
            region.h = h
            region.is_reference_obj = is_reference_obj
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
                # 将大图id, 区域坐标id, 轮廓id(自身的id), 是否为参考对象一起返回
                contour['img_id'] = pk
                contour['region_id'] = region.id
                contour['contours_id'] = contour_obj.id
                contour['is_reference_obj'] = region.is_reference_obj

            # ----- 返回参考对象最新的灰度平均值 ------ #
            if is_reference_obj == 1:
                # 定义列表存储所有参考对象的灰度值
                gray_value_list = []
                # 直接查询该大图所有的参考对象
                all_reference = Image.objects.get(id=pk).regions.filter(is_reference_obj=True)
                # 判断该大图是否有参考对象
                if all_reference:
                    # 循环所有参考对象, 将灰度值添加到列表
                    for obj in all_reference:
                        gray_value_list.extend(obj.contours.values_list('cells_contours_gray', flat=True))
                    # 计算灰度值平均值
                    gray_avg = round(np.average(gray_value_list), 2)
                else:
                    gray_avg = None
            else:
                gray_avg = None

            # 最终返回结果
            return Response(status=status.HTTP_200_OK,
                            data={'contours_info': contours_info, 'gray_avg': gray_avg})

        else:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={'msg': '请输入正确的参数！'})

    def delete(self, request, pk):

        # 根据轮廓id, 查询数据库对象
        try:
            contour_obj = ContoursMark.objects.get(id=pk, is_delete=False)
        except ContoursMark.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND, data={'msg': '数据不存在！'})

        try:
            # 判断是否该细胞核轮廓所在的区域是否只剩下最后一个, 如果是最后一个, 则连该区域也删除
            last_count = contour_obj.region.contours.count()
            if last_count == 1:
                # 删除区域, 也会将轮廓一起删除
                RegionCoord.objects.get(id=contour_obj.region.id).delete()
            else:
                contour_obj.delete()
        except Exception as e:
            logger.warning(e)
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR, data={'msg': '数据库删除失败！'})

        return Response(status=status.HTTP_204_NO_CONTENT, data={'msg': '删除细胞核轮廓成功！'})


class CUReferenceView(APIView):
    """
    patch: 设置区域或修改区域是否为参考对象
    """

    def patch(self, request, pk):

        # 获取参考对象设置值
        is_reference_obj = request.data.get('is_reference_obj', None)
        if is_reference_obj is None:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={'msg': '请输入正确的参数！'})

        # 根据轮廓id, 查询数据库对象
        try:
            region = RegionCoord.objects.get(id=pk, is_delete=False)
        except ContoursMark.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND, data={'msg': '数据不存在！'})

        # 修改是否为参考对象
        region.is_reference_obj = is_reference_obj
        region.save()

        # ----- 返回参考对象最新的灰度平均值 ------ #
        # 定义列表存储所有参考对象的灰度值
        gray_value_list = []
        # 通过region_id反向查询大图id
        image_id = region.image.id
        # 查询该大图所有的参考对象
        all_reference = Image.objects.get(id=image_id).regions.filter(is_reference_obj=True)
        # 判断该大图是否有参考对象
        if all_reference:
            # 循环所有参考对象, 将灰度值添加到列表
            for obj in all_reference:
                gray_value_list.extend(obj.contours.values_list('cells_contours_gray', flat=True))
            # 计算灰度值平均值
            gray_avg = round(np.average(gray_value_list), 2)
        else:
            gray_avg = None

        return Response(status=status.HTTP_200_OK, data={
            'region_id': pk, 'is_reference_obj': is_reference_obj, 'gray_avg': gray_avg
        })


class DRegionView(APIView):
    """
    delete: 物理删除一条区域坐标记录
    """

    def delete(self, request, pk):

        # 根据区域id, 查询数据库对象
        try:
            region = RegionCoord.objects.get(id=pk, is_delete=False)
        except RegionCoord.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND, data={'msg': '数据不存在！'})

        try:
            # 数据库中物理删除, 同时级联删除其它外键关联
            region.delete()
        except Exception as e:
            logger.warning(e)
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR, data={'msg': '数据库删除失败！'})

        # ----- 返回参考对象最新的灰度平均值 ------ #
        if region.is_reference_obj == 1:
            # 定义列表存储所有参考对象的灰度值
            gray_value_list = []
            # 通过region_id反向查询大图id
            image_id = region.image.id
            # 查询该大图所有的参考对象
            all_reference = Image.objects.get(id=image_id).regions.filter(is_reference_obj=True)
            # 判断该大图是否有参考对象
            if all_reference:
                # 循环所有参考对象, 将灰度值添加到列表
                for obj in all_reference:
                    gray_value_list.extend(obj.contours.values_list('cells_contours_gray', flat=True))
                # 计算灰度值平均值
                gray_avg = round(np.average(gray_value_list), 2)
            else:
                gray_avg = None
        else:
            gray_avg = None

        return Response(status=status.HTTP_200_OK,
                        data={'msg': '删除整个区域成功！', 'gray_avg': gray_avg})
