from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, ListCreateAPIView, GenericAPIView

from Patient.models import Patient
from Case.models import Case
from Image.models import Image
from Patient.serializers import SCPatientSerializer, UPatientSerializer

import logging
logger = logging.getLogger('qas')


class SCPatientView(APIView):

    """
    get: 查询一条病人的记录
    post: 新增一条病人的记录
    patch: 修改一条病人的记录
    """

    def get(self, request):

        # 获取查询字符串中的参数
        img_id = request.GET.get('img_id', None)
        if not img_id:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={'msg': '参数错误！'})

        # 根据大图id, 查询数据库
        try:
            # 大图id -> 病例信息(反向查询) -> 其对应的病人信息(正向查询)
            image = Image.objects.get(id=img_id, is_delete=False)
        except Exception as e:
            logger.error(e)
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR, data={'msg': '数据不存在！'})

        try:
            patient = image.icase.patient
        except Exception as e:
            logger.error(e)
            return Response(status=status.HTTP_200_OK, data={'msg': '没有该病人信息', 'res_info': None})

        # 序列化返回
        ser = SCPatientSerializer(patient)
        # 添加诊断结果返回
        res_info = ser.data
        res_info['diagnose_label'] = image.icase.diagnose_label

        return Response(status=status.HTTP_200_OK, data={'res_info': res_info})

    def post(self, request):

        # 新建报告前没有病人的id, 因此获取到的是大图的id
        img_id = request.data.get('id', None)
        if not img_id:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={'msg': '参数错误！'})

        # 不保存diagnose_label/patient_id到数据库, 因为patient表不包含这两个字段
        request.data.pop('id')
        try:
            diagnose_label = request.data.pop('diagnose_label')
        except Exception as e:
            diagnose_label = None

        # 获取参数, 校验参数
        ser = SCPatientSerializer(data=request.data)
        # 验证通过则保存病人的信息, 得到病人的id
        if ser.is_valid():
            ser.save()
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST, data='参数错误！')

        # 同时将新建的病人信息id, 大图id保存到病例信息表
        try:
            case = Case.objects.create(
                diagnose_label=diagnose_label,
                image=Image.objects.get(id=img_id),
                patient=Patient.objects.get(id=ser.data['id'])
            )
        except Exception as e:
            logger.error(e)
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR, data='数据库保存失败！')

        # 添加诊断结果返回
        res_info = ser.data
        res_info['diagnose_label'] = case.diagnose_label

        return Response(status=status.HTTP_201_CREATED, data={'res_info': res_info})

    def patch(self, request):

        # 修改报告, 前端传来的大图的id
        img_id = request.data.get('id', None)
        if not img_id:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={'msg': '参数错误！'})

        # 不保存diagnose_label/img_id到数据库, 因为patient表不包含这两个字段
        try:
            diagnose_label = request.data.pop('diagnose_label')
        except Exception as e:
            diagnose_label = None

        # 根据id, 查询数据库对象
        try:
            patient = Patient.objects.get(id=img_id, is_delete=False)
        except Patient.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND, data={'msg': '数据不存在！'})

        # 获取参数, 校验参数, 保存结果
        ser = UPatientSerializer(patient, data=request.data)
        # 验证通过则保存, 否则返回错误
        if ser.is_valid():
            ser.save()
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST, data='参数错误！')

        # 通过病人反向查询其病例信息
        case_id = patient.pcase.id
        # 同时保存诊断结果到病例表中
        case = Case.objects.get(id=case_id)
        case.diagnose_label = diagnose_label
        case.save()

        # 添加诊断结果返回
        res_info = ser.data
        res_info['diagnose_label'] = case.diagnose_label

        return Response(status=status.HTTP_200_OK, data={'res_info': res_info})
