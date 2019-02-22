from django.db import models


class Image(models.Model):
    """大图信息"""

    id = models.AutoField(primary_key=True, verbose_name=u'唯一主键')
    file_name = models.CharField(max_length=128, verbose_name=u'文件名', null=True, blank=True)
    suffix = models.CharField(max_length=16, verbose_name=u'文件后缀名', null=True, blank=True)
    storage_path = models.CharField(max_length=256, verbose_name=u'存储路径', null=True, blank=True)
    last_open_time = models.DateTimeField(verbose_name=u'上次打开时间', null=True, blank=True)
    file_size = models.CharField(max_length=16, verbose_name=u'文件大小', null=True, blank=True)

    is_delete = models.BooleanField(verbose_name=u'是否逻辑删除', default=False)
    create_time = models.DateTimeField(verbose_name=u'创建时间', auto_now_add=True)
    update_time = models.DateTimeField(verbose_name=u'更新时间', auto_now=True)

    class Meta:
        db_table = 'tb_image'  # 自定义数据库表的名称
        verbose_name = '大图信息'  # 在后台admin中显示表的中文名
        verbose_name_plural = verbose_name

    def __str__(self):
        return '当前文件名为：%s' % self.file_name
