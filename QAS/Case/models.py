from django.db import models
from Patient.models import Patient
from Image.models import Image


class Case(models.Model):
    """
    病例信息
    """

    id = models.AutoField(primary_key=True, verbose_name=u'唯一主键')

    image = models.OneToOneField(Image, on_delete=models.CASCADE, related_name='icase', blank=True, null=True,
                                 verbose_name=u'病理图像')
    patient = models.OneToOneField(Patient, on_delete=models.CASCADE, related_name='pcase', blank=True, null=True,
                                   verbose_name=u'患者')
    diagnose_label = models.CharField(max_length=256, verbose_name=u'诊断标签', null=True, blank=True)

    create_time = models.DateTimeField(verbose_name=u"创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name=u"处理时间", auto_now=True)

    def __str__(self):
        return '该病例信息对应的大图id为: %s, 对应的病人id为: %s' % (self.image.id, self.patient.id)

    class Meta:
        db_table = 'tb_case'  # 自定义数据库表的名称
        verbose_name = u'病例信息'
        verbose_name_plural = verbose_name
