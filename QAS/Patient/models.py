from django.db import models


class Patient(models.Model):
    """
    患者信息
    """

    GENDER_CHOICES = (
        ("MALE", "男"),
        ("FEMALE", "女"),
    )

    id = models.AutoField(primary_key=True, verbose_name=u'唯一主键')

    # 个人信息
    name = models.CharField(max_length=32, verbose_name=u"姓名", null=True, blank=True)
    age = models.IntegerField(verbose_name=u"年龄", null=True, blank=True)
    gender = models.CharField(max_length=8, default="FEMALE", choices=GENDER_CHOICES, verbose_name=u"性别")

    # 病理信息
    specimen_source = models.CharField(max_length=32, verbose_name=u'标本来源', blank=True, null=True)
    report_time = models.DateTimeField(verbose_name=u'报告时间', blank=True, null=True)
    send_time = models.DateTimeField(verbose_name=u"送检时间", blank=True, null=True)

    create_time = models.DateTimeField(verbose_name=u"创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name=u"更新时间", auto_now=True)

    def __str__(self):
        return '用户名为：%s' % self.name

    class Meta:
        db_table = 'tb_patient'  # 自定义数据库表的名称
        verbose_name = u'患者信息'
        verbose_name_plural = verbose_name
