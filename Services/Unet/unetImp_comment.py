# !/usr/bin/env python3
# -*- encoding: utf-8 -*-
# @author: condi
# @file: unetImp_comment.py
# @time: 19-1-27 下午3:01


import os
import shutil

import cv2
import numpy as np
from numpy import set_printoptions
import mxnet as mx
from collections import namedtuple
from Services.utils import get_coord
set_printoptions(threshold=np.nan)

def get_segmentation_mod(prefix='/home/kyfq/MyPython/PycharmProjects/qas/Services/Unet/segnet_bb5_final', epoch=0, seg_data_shape=128, batch_size=1, ctx=mx.gpu(0)):
# def get_segmentation_mod(prefix='./segnet_bb5_final', epoch=0, seg_data_shape=128, batch_size=1, ctx=mx.gpu(0)):
    """
    训练一个神经网络需要一些步骤。比如指定训练数据的输入，模型参数初始化，执行前向和后向计算，梯度下降并更新参数，模型的保存和恢复等
    加载unet权重
    :param prefix: prefix of model name
    :param epoch: number of iterations of the model. model name = prefix + '-' + epoch + '.params'
    :param seg_data_shape: initialize the network with input shape
    :param batch_size: batch size
    :param ctx: select gpu (mx.gpu(0))
    :return: the Unet model
    """

    # epoch: 我们想要加载哪个epoch（一般是加载测试效果最好的那个epoch）
    sym, arg_params, aux_params = mx.model.load_checkpoint(prefix, epoch)

    # symbol: 定义好的网络，即前向计算时的最后一层的输出结果所保存的变量
    # context：用于执行计算的硬件列表（CPU，GPU）
    # data_names：输入数据的变量名列表
    # label_names：输入标签的变量名列表
    mod = mx.mod.Module(symbol=sym, context=ctx, data_names=['data'], label_names=None)

    # mod.bind的操作是在显卡上分配所需的显存，用以准备计算环境
    # batch_size=1, 说明输入一张图片, 不是输入多张
    # seg_data_shape： 随便输入？？
    mod.bind(for_training=False, data_shapes=[('data', (batch_size, 3, seg_data_shape, seg_data_shape))],
             label_shapes=None)

    # 导入参数列表
    # arg_params：网络的权重
    # aux_params：网络的梯度？
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
    # formula: dst = src1 * alpha + src2 * beta + gamma;
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

    # ？
    cls_mean_val = np.array([[[107]], [[107]], [[107]]])
    cls_std_scale = 1.0

    # 输入的img的维度: (54, 60, 3)
    # 转置后的img的维度: (3, 54, 60)
    img = np.transpose(img, (2, 0, 1))
    # 增加一个维度后的img的维度: (1, 3, 62, 67)
    img = img[np.newaxis, :]

    img = cls_std_scale * (img.astype(np.float32) - cls_mean_val)

    # 使用mx.nd.array: 将numpy的ndarray类型转换成mxnet中的NDArray类型
    # mod.forward: 执行前向传播计算
    mod.forward(Batch([mx.nd.array(img)]))

    # 返回预测结果(每个像素点的概率)
    # 预测的结果的维度变成了(1, 2, 54, 60)，2是因为最后结果是：一张前景图和一张背景图
    pred = mod.get_outputs()[0].asnumpy()

    # axis=1: 表示对层数那维进行对比，对比返回最大值的坐标, 因为只有2维, 因此结果不是1对就0
    # 最后返回一个图片中, 大的属于前景, 小的属于背景
    # [0,0,0,...,1]
    # [...........]
    # [0,1,0,...,0]
    pred = np.argmax(pred, axis=1)[0]

    return pred


def find_max_contour(pred, raw_img):
    """
    找出最大的连同区域, 寻找图像轮廓
    :param pred: predicted results from seg_img()
    :return:
    """

    # 版本不同, cv2.findContours返回的参数个数不一样
    # findContours:
    # 第一个参数：经二值化后的图像, 不可以是灰度图
    # 第二个参数：表示轮廓的检索模式
    #   cv2.RETR_EXTERNAL：表示只检测外轮廓
    #   cv2.RETR_LIST：检测的轮廓不建立等级关系
    #   cv2.RETR_CCOMP：建立两个等级的轮廓，上面的一层为外边界，里面的一层为内孔的边界信息。如果内孔内还有一个连通物体，这个物体的边界也在顶层。
    #   cv2.RETR_TREE：建立一个等级树结构的轮廓
    # 第三个参数method：表示轮廓的近似办法
    #   cv2.CHAIN_APPROX_NONE：存储所有的轮廓点
    #   cv2.CHAIN_APPROX_SIMPLE：会压缩轮廓，将轮廓上冗余点去掉，比如说四边形就会只储存四个角点。
    img3, contours, hierarchy = cv2.findContours(pred, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)

    # 将在图中找到的所有contours, 使用cv2.contourArea统计面积, 并按面积大小降序
    contours = sorted(contours, key=cv2.contourArea, reverse=True)

    # 对排序后的contours, 取第一个得到最大的面积
    # print('图像：%s, 面积为：%s' % (i, cv2.contourArea(contours[0])))
    # 可能unet找不到，因此contours为[]，从而引发错误
    try:
        # area_list.append(cv2.contourArea(contours[0]))
        # 计算轮廓面积
        max_area = cv2.contourArea(contours[0])
        # 计算轮廓周长, 参数2表示轮廓是否封闭，显然轮廓是封闭的
        max_perimeter = cv2.arcLength(contours[0], True)

    except Exception as e:
        contours = None
        max_area = None
        max_perimeter = None

    # np.zeros_like会创建一个与pred一样维度的数组, 内容全为0, 因此会创建一个黑色画布
    mask_contour = np.zeros_like(pred)
    try:
        # drawContours:
        # 第一个参数是一张图片，可以是原图或者其他
        # 第二个参数是轮廓，也可以说是cv2.findContours()找出来的点集，一个列表。
        # 第三个参数是：要画哪个轮廓，给出其在contours列表中的索引,因为上面已对contours进行降序，因此获取第一个即为最大的轮廓
        #             若要全部绘制可设为-1
        # 第四个参数为：轮廓的颜色
        # 第五个参数为：轮廓的厚度(当thickness为-1时，会绘制轮廓里面的面积, 而指定厚度为1时, 即绘制出轮廓
        # cv2.drawContours(mask_contour, contours, 0, color=255, thickness=1)
        cv2.drawContours(mask_contour, contours, 0, color=(255,255,255), thickness=-1)
        return mask_contour, contours, max_area, max_perimeter
    except Exception as e:
        return pred, contours, max_area, max_perimeter


def segment(detect_dir, save_dir, segment_model, flag='unet'):

    # 创建存储目录
    os.makedirs(save_dir, exist_ok=True)

    # 定义保存细胞核信息的列表
    contours_info = []

    # 对yolo检测出来的所有细胞进行分割
    yolo_detect_cells_list = os.listdir(detect_dir)

    for file_name in yolo_detect_cells_list:
        # 读取图片
        fn_path = os.path.join(detect_dir, file_name)
        raw_img = cv2.imread(fn_path)

        # 图像亮度处理
        raw_img_light = contrast_brightness_image(raw_img)

        # 分割
        pred = seg_img(raw_img_light, segment_model).astype(np.uint8)

        # 找最大连同区域
        # 如果检测到细胞核的话, pred接收到的是细胞核的全部像素点坐标而非轮廓(因此设置了thickness=-1), 否则为None
        pred, contours, max_area, max_perimeter = find_max_contour(pred, file_name)

        # 计算灰度值
        # pred为细胞核的坐标值, 需要转换成0-1矩阵, 识别到的地方为1, 没有的为0
        zero_one_matrix = np.where(pred > 0, 1, 0) if pred is not None else None

        # 图像灰度化处理
        gray_img = cv2.cvtColor(raw_img, cv2.COLOR_RGB2GRAY)
        # 像素重新计算(图像中颜色深的像素的值越接近于0, 越浅的颜色越接近于255,
        # 而在细胞核灰度中, 如果细胞核颜色越深的话, 其灰度值应该越大, 因此需要将其进行颜色值调换)
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
