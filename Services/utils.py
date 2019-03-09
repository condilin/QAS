# !/usr/bin/env python3
# -*- encoding: utf-8 -*-
# @author: condi
# @file: utils.py
# @time: 19-1-29 下午8:24

import cv2
import math
import re
import os
import numpy as np


class PaddingTiles(object):
    """resize图像成608x608"""

    def __init__(self):
        self.__black_border = [0, 0, 0]
        self.__white_border = [255, 255, 255]

    def padding_around(self, img_height, img_width):
        """扩展四周的像素"""

        extend_up = math.ceil((608 - img_height) / 2)
        extend_down = math.floor((608 - img_height) / 2)
        extend_left = math.ceil((608 - img_width) / 2)
        extend_right = math.floor((608 - img_width) / 2)
        return extend_up, extend_down, extend_left, extend_right

    def padding_right_bottom(self, img_height, img_width):
        """扩展底部和右边的像素"""

        extend_up = 0
        extend_down = 608 - img_height
        extend_left = 0
        extend_right = 608 - img_width
        return extend_up, extend_down, extend_left, extend_right

    def padding_tiles(self, img_path, current_time, coord, padding_methods='around', padding_border='white'):

        img = cv2.imread(img_path)

        # 获取图像的宽高及通道数
        img_height, img_width, img_channels = img.shape

        if 0 < img_height < 608 and 0 < img_width < 608:

            # padding methods
            if padding_methods == 'around':
                extend_up, extend_down, extend_left, extend_right = self.padding_around(img_height, img_width)
            else:
                extend_up, extend_down, extend_left, extend_right = self.padding_right_bottom(img_height, img_width)

            # padding_border
            # src：要处理的原图
            # top, bottom, left, right：上下左右要扩展的像素数
            # borderType：边框类型(BORDER_CONSTANT为常数)
            if padding_border == 'white':
                res = cv2.copyMakeBorder(
                    img, extend_up, extend_down, extend_left, extend_right,
                    cv2.BORDER_CONSTANT, value=self.__white_border
                )
            else:
                res = cv2.copyMakeBorder(
                    img, extend_up, extend_down, extend_left, extend_right,
                    cv2.BORDER_CONSTANT, value=self.__black_border
                )

            # 保存图像
            cv2.imwrite(
                './Services/Yolo/padding_detect_img/screenshot_padding_{}_{}.png'.format(current_time, coord), res
            )

            # 返回补边左上的像素, 用于


def get_coord(file_name):
    """
    获取图像在框选区域中的坐标
    """

    _file, suffix = os.path.splitext(file_name)
    res = re.match(r'.+_x(\d+)_y(\d+)_w(\d+)_h(\d+)', _file)
    x, y, w, h = res.group(1), res.group(2), res.group(3), res.group(4)
    # 返回整数坐标宽高
    return int(x), int(y), int(w), int(h)
