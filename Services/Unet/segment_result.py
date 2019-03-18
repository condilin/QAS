# !/usr/bin/env python3
# -*- encoding: utf-8 -*-
# @author: condi
# @file: segment_result.py
# @time: 19-3-9 下午7:59

import os
import shutil
import cv2
import numpy as np
import mxnet as mx
from collections import namedtuple
from Services.utils import get_coord

os.environ['MXNET_CUDNN_AUTOTUNE_DEFAULT'] = '0'


def get_segmentation_mod(prefix='/home/kyfq/MyPython/PycharmProjects/qas/Services/Unet/segnet_bb5_final', epoch=0, seg_data_shape=128, batch_size=1, ctx=mx.gpu(0)):

    sym, arg_params, aux_params = mx.model.load_checkpoint(prefix, epoch)
    mod = mx.mod.Module(symbol=sym, context=ctx, data_names=['data'], label_names=None)
    mod.bind(for_training=False, data_shapes=[('data', (batch_size, 3, seg_data_shape, seg_data_shape))],
             label_shapes=None)
    mod.set_params(arg_params=arg_params, aux_params=aux_params)
    return mod


def contrast_brightness_image(img, a=1.8, b=-90):
    """
    调整亮度
    :param img: ouput image of Yolo detection
    :param a: coefficient a, img * a + b
    :param b: coefficient b, img * a + b
    :return: contrast enhanced  image
    """

    h, w, ch = img.shape
    src2 = np.zeros([h, w, ch], img.dtype)
    dst = cv2.addWeighted(img, a, src2, 1-a, b)
    return dst


def seg_img(img, mod):
    """
    使用unet模型进行前向计算，对图像进行图像分割
    :param img: ouput image of Yolo detection
    :param mod: Unet model
    :return: predicted results
    """

    Batch = namedtuple('Batch', ['data'])

    cls_mean_val = np.array([[[107]], [[107]], [[107]]])
    cls_std_scale = 1.0
    img = np.transpose(img, (2, 0, 1))
    img = img[np.newaxis, :]
    img = cls_std_scale * (img.astype(np.float32) - cls_mean_val)

    mod.forward(Batch([mx.nd.array(img)]))
    pred = mod.get_outputs()[0].asnumpy()
    pred = np.argmax(pred, axis=1)[0]
    return pred


def find_max_contour(pred):
    """
    找出最大的连同区域, 寻找图像轮廓
    :param pred: predicted results from seg_img()
    :return:
    """

    img3, contours, hierarchy = cv2.findContours(pred, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    try:
        max_area = cv2.contourArea(contours[0])
        max_perimeter = cv2.arcLength(contours[0], True)

    except Exception as e:
        contours = None
        max_area = None
        max_perimeter = None

    mask_contour = np.zeros_like(pred)
    try:
        cv2.drawContours(mask_contour, contours, 0, color=(255,255,255), thickness=-1)
        return mask_contour, contours, max_area, max_perimeter
    except Exception as e:
        return pred, contours, max_area, max_perimeter


def segment(detect_dir, save_dir, flag='unet'):

    os.makedirs(save_dir, exist_ok=True)

    contours_info = []
    yolo_detect_cells_list = os.listdir(detect_dir)
    seg_mod = get_segmentation_mod()
    for file_name in yolo_detect_cells_list:
        # 读取图片
        fn_path = os.path.join(detect_dir, file_name)
        raw_img = cv2.imread(fn_path)

        # 图像亮度处理
        raw_img_light = contrast_brightness_image(raw_img)

        # 分割
        pred = seg_img(raw_img_light, seg_mod).astype(np.uint8)

        # 找最大连同区域
        pred, contours, max_area, max_perimeter = find_max_contour(pred)

        # 计算灰度值
        zero_one_matrix = np.where(pred > 0, 1, 0) if pred is not None else None
        gray_img = cv2.cvtColor(raw_img, cv2.COLOR_RGB2GRAY)
        gray_img_resort = 255 - gray_img
        cells_contours_gray = np.sum(zero_one_matrix * gray_img_resort)

        # 获取框选区域坐标
        if flag == 'yolo':
            region_x, region_y, region_w, region_h = get_coord(file_name)
        else:
            region_x, region_y, region_w, region_h = (None, None, None, None)

        contours_info.append(
            {
                'cells_contours_coord': contours[0] if contours else None,
                'cells_contours_area': round(max_area) if max_area is not None and max_area != 0 else None,
                'cells_contours_perimeter': round(max_perimeter) if max_perimeter else None,
                'cells_contours_gray': int(cells_contours_gray) if cells_contours_gray else None,
                'region_coord_x': region_x,
                'region_coord_y': region_y,
                'region_coord_w': region_w,
                'region_coord_h': region_h,
            }
        )

    # 删除yolo已检测的/或待检测的目录, 然后再创建一个空的文件夹
    shutil.rmtree(detect_dir)
    os.makedirs(detect_dir, exist_ok=True)

    return contours_info


if __name__ == "__main__":

    # 保存面积列表
    area_list = []

    p,c = segment('/home/kyfq/MyPython/PycharmProjects/qas/Services/Yolo/detected_img/',
                  '/home/kyfq/MyPython/PycharmProjects/qas/Services/Unet/segmented_img/')
    print(c)
