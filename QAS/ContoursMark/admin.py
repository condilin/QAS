from django.contrib import admin
from . import models
# Register your models here.


@admin.register(models.ContoursMark)
class ImageAdmin(admin.ModelAdmin):

    # ------ 列表页的显示 ------- #

    # 在文章列表页面显示的字段, 不是详情里面的字段
    list_display = ['id']

    # 设置哪些字段可以点击进入编辑界面
    list_display_links = ('id', )

    # 每页显示10条记录
    list_per_page = 10

    # 按最新创建的时间排序. ordering设置默认排序字段，负号表示降序排序
    ordering = ('-update_time',)

    # 搜索栏
    search_fields = ['id']

    # 过滤器
    list_filter = ['id']
