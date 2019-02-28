from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, ListCreateAPIView, GenericAPIView

from Patient.models import Patient
from Case.models import Case
from Image.models import Image
from Patient.serializers import PatientSerializer

import logging
logger = logging.getLogger('qas')


class SCPatientView(APIView):

    """
    get: 查询一条病人的记录
    post: 新增一条病人的记录
    """

    def get(self, request):

        # 获取查询字符串中的参数
        img_id = request.GET.get('img_id')

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
        ser = PatientSerializer(patient)
        return Response(status=status.HTTP_200_OK, data={'res_info': ser.data})

    def post(self, request):

        # 不保存diagnose_label和img_id到数据库, 因为patient表不包含这两个字段
        diagnose_label = request.data.pop('diagnose_label')
        img_id = request.data.pop('img_id')

        # 获取参数, 校验参数
        serializer = PatientSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # 同时将新建的病人信息id, 大图id保存到病例信息表
        try:
            Case.objects.create(
                diagnose_label=diagnose_label,
                image=Image.objects.get(id=img_id),
                patient=Patient.objects.get(id=serializer.data['id'])
            )
        except Exception as e:
            logger.error(e)
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR, data='数据库保存失败！')

        # 返回结果
        return Response(status=status.HTTP_201_CREATED, data=serializer.data)

    def patch(self, request):

        # 根据id, 查询数据库对象
        try:
            patient = Patient.objects.get(id=request.data['id'], is_delete=False)
        except Patient.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND, data={'msg': '数据不存在！'})

        # 获取参数, 校验参数, 保存结果
        serializer = PatientSerializer(patient, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)
