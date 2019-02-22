from django.db import models
from Image.models import Image


class RegionCoord(models.Model):
    """用户框出的区域坐标信息"""

    id = models.AutoField(primary_key=True, verbose_name=u'唯一主键')

    image = models.ForeignKey(
        Image, on_delete=models.CASCADE, related_name='regions', verbose_name=u"关联病理图像id"
    )
    x = models.IntegerField(verbose_name=u'标注点左上角坐标-x')
    y = models.IntegerField(verbose_name=u'标注点左上角坐标-y')
    w = models.IntegerField(verbose_name=u'标注点细胞宽度-w')
    h = models.IntegerField(verbose_name=u'标注点细胞高度-h')
    is_reference_obj = models.BooleanField(verbose_name=u'是否为参考对象', default=False)

    is_delete = models.BooleanField(verbose_name=u'是否逻辑删除', default=False)
    create_time = models.DateTimeField(verbose_name=u'创建时间', auto_now_add=True)
    update_time = models.DateTimeField(verbose_name=u'更新时间', auto_now=True)

    class Meta:
        db_table = 'tb_region_coord'  # 自定义数据库表的名称
        verbose_name = '区域坐标信息'  # 在后台admin中显示表的中文名
        verbose_name_plural = verbose_name

    def __str__(self):
        return '该区域坐标所属的大图为: %s' % self.image


class ContoursMark(models.Model):
    """细胞轮廓标记信息"""

    id = models.AutoField(primary_key=True, verbose_name=u'唯一主键')

    region = models.ForeignKey(
        RegionCoord, on_delete=models.CASCADE, related_name='contours', verbose_name=u"关联用户框的区域表id"
    )
    cells_contours_coord = models.CharField(max_length=3072, verbose_name=u"细胞轮廓坐标")
    cells_contours_area = models.IntegerField(verbose_name=u"细胞轮廓面积")
    cells_contours_perimeter = models.IntegerField(verbose_name=u"细胞轮廓周长")
    cells_contours_gray = models.IntegerField(verbose_name=u"细胞轮廓里的灰度值")

    is_delete = models.BooleanField(verbose_name=u'是否逻辑删除', default=False)
    create_time = models.DateTimeField(verbose_name=u'创建时间', auto_now_add=True)
    update_time = models.DateTimeField(verbose_name=u'更新时间', auto_now=True)

    class Meta:
        db_table = 'tb_contours_mark'  # 自定义数据库表的名称
        verbose_name = '细胞轮廓标记信息'  # 在后台admin中显示表的中文名
        verbose_name_plural = verbose_name

    def __str__(self):
        return '该轮廓所属的区域坐标为: (%s,%s,%s,%s)' % (
            self.region.x, self.region.y, self.region.w, self.region.h
        )
