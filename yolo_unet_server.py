# !/usr/bin/env python3
# -*- encoding: utf-8 -*-
# @author: condi
# @file: yolo_unet_server.py
# @time: 19-2-12 下午3:36
import shutil

import cv2
import os, time
import numpy as np
import requests
import logging

from flask import Flask, make_response, jsonify, request
from flask_cors import CORS

from Services.Aslide.aslide import Aslide
from Services.Yolo.detect_result import YoloInterface
from Services.Unet.segment_result import segment, get_segmentation_mod

# 实例化yolo检测对象, 加载yolo权重
yolo_instance = YoloInterface()
# 加载unet权重
unet_model_weight = get_segmentation_mod()


app = Flask(__name__)
# 跨域支持
CORS(app)
app.secret_key = 'xfsdfsEESdf3#$#423df$%#324qwGR'

tif_path_cache = {}
slide_cache = {}

QAS_HOST = '192.168.2.179:8010'
TIF_PATH_PREX = '/run/user/1000/gvfs/smb-share:server=192.168.2.221,share='

# yolo待检测的图像
yolo_wait_detect_img_path = './Services/Yolo/wait_detect_img/screenshot_{}.png'
# yolo待检测的图像的目录
yolo_wait_detect_dir_path = './Services/Yolo/wait_detect_img'
# yolo已检测的图像路径
save_yolo_detect = './Services/Yolo/detected_img'
# 保存unet分割后的图像路径
save_unet_segment = './Services/Unet/segmented_img'


# 配置日志/初始化变量
class ConfigLog(object):
    def __init__(self):
        # 日志输出的位置
        self.log_name = '/home/kyfq/MyPython/PycharmProjects/qas/QAS/QAS/logs/cell_image_server.log'
        # 输出格式
        self.log_format = logging.Formatter('%(levelname)s [%(asctime)s] %(message)s')

        # logging配置
        handler = logging.FileHandler(self.log_name, encoding='UTF-8')
        # 设置级别
        handler.setLevel(logging.WARNING)
        # 设置输出格式
        handler.setFormatter(self.log_format)
        app.logger.addHandler(handler)

        # yolo/unet模型中要创建保存和检测的图像的路径
        if os.path.exists(yolo_wait_detect_dir_path):
            shutil.rmtree(yolo_wait_detect_dir_path)
            os.makedirs(yolo_wait_detect_dir_path, exist_ok=True)
        if os.path.exists(save_yolo_detect):
            shutil.rmtree(save_yolo_detect)
            os.makedirs(save_yolo_detect, exist_ok=True)
        if os.path.exists(save_unet_segment):
            shutil.rmtree(save_unet_segment)
            os.makedirs(save_unet_segment, exist_ok=True)


def get_path(image_id):
    try:
        if image_id in tif_path_cache:
            tif_path = tif_path_cache[image_id]
        else:
            tiff_url = 'http://%s/api/v1/images/%s/' % (QAS_HOST, image_id)
            response = requests.get(tiff_url)

            if response.status_code != 200:
                raise Exception('can not get resource', response.status_code, response.content)
            image_info = response.json()
            tif_path = os.path.join(image_info['storage_path'], image_info['file_name']+image_info['suffix'])
            tif_path_cache[image_info['id']] = tif_path
        return tif_path
    except Exception as e:
        app.logger.error('获取图像路径失败：%s' % e)


def get_slide(image_id, img_path):
    """
    get tiles and cache
    :param img_path:
    :return:
    """
    img_name = os.path.basename(img_path)
    img = str(image_id) + '_' + img_name

    try:
        if img in slide_cache:
            slide = slide_cache[img]
        else:
            slide = Aslide(img_path)
            slide_cache[img] = slide

        return slide
    except Exception as e:
        app.logger.error('读取图像失败：%s' % e)


@app.route("/tiles/<image_id>/<int:x>/<int:y>/<int:w>/<int:h>")
def cell_image_request(image_id, x, y, w, h):
    """
    get cell image
    :param request:
    :param image_id: id of tiff image
    :param x: coordinate-x
    :param y: coordinate-y
    :param w: image width
    :param h: image height
    :return:
    """

    start_time = time.time()

    # 判断框选区域的图像的是否太小
    if int(w) < 10 or int(h) < 10 or int(w) > 3000 or int(h) > 3000:
        end_time = time.time()
        # 直接返回空信息
        return make_response(jsonify({
            'contours_info': [],
            'msg': '面积过小或过大！',
            'cost_time': end_time - start_time
        }))

    # 根据id, 读取图像
    slide = get_slide(image_id, get_path(image_id))
    # 根据(x,y), w, h切图
    tile_image = slide.read_region((x, y), 0, (w, h))

    # 保存需要待检测的图像
    yolo_wait_detect_img_path_ts = yolo_wait_detect_img_path.format(int(time.time()*1000))
    tile_image.save(yolo_wait_detect_img_path_ts)

    # 加载yolo模型对图像进行细胞检测(params1: input_img_path, params2: output_dir_path)
    yolo_instance.get_detect_img(yolo_wait_detect_img_path_ts, save_yolo_detect)

    # yolo可能对单个细胞检测不到或置信度很低, 此时直接使用unet进行预测, 可能效果会好点
    detected_img_count = os.listdir(save_yolo_detect)
    # 加载unet模型, 获取分割后细胞核信息
    if not detected_img_count:
        contours_info = segment(yolo_wait_detect_dir_path, save_unet_segment, unet_model_weight, flag='unet')
    else:
        contours_info = segment(save_yolo_detect, save_unet_segment, unet_model_weight, flag='yolo')
        # 检测完之后删除待检测的图像
        os.remove(yolo_wait_detect_img_path_ts)

    # 获取原图的坐标
    raw_img_cord = np.array([x, y])

    # 获取真实坐标
    for contour in contours_info:
        # unet输入的小图,得到的坐标
        unet_input_coord = contour['cells_contours_coord']

        # 判断是否检测到细胞, 检测不到则返回None
        if unet_input_coord is not None:
            # 判断是否只使用unet检测
            if contour['region_coord_x']:
                # 加上所框选的区域的坐标
                region_cord = np.array([contour['region_coord_x'], contour['region_coord_y']])
                # 细胞核真实的坐标 = 细胞核在unet框选区域小图中的坐标 + 框选区域小图在大图的坐标
                real_cord = unet_input_coord + raw_img_cord + region_cord
            else:
                real_cord = unet_input_coord + raw_img_cord
            # 将结果拉直为一维向量,再将ndarrary类型转换成list类型返回到前端
            real_cord_flatten = real_cord.flatten().tolist()

            # 返回细胞核在原图的真实坐标
            contour['cells_contours_coord'] = real_cord_flatten
        else:
            contour['cells_contours_coord'] = None

    end_time = time.time()
    # 返回contours坐标以及areas等信息
    return make_response(jsonify({
        'contours_info': contours_info, 'cost_time': end_time-start_time
    }))


@app.route("/contours/<int:image_id>", methods=["POST"])
def contours_compute(image_id):
    """
    修改/添加细胞核轮廓坐标, 重新计算面积和灰度值
    :param image_id:
    :return:
    """

    # 获取x-www-form-urlencoded类型并转换成dict类型
    request_form_to_dict = request.form.to_dict()

    # 获取表单中的参数
    x = request_form_to_dict.get('x', None)
    y = request_form_to_dict.get('y', None)
    w = request_form_to_dict.get('w', None)
    h = request_form_to_dict.get('h', None)
    # 获取细胞轮廓坐标, 转换成如(x, 1, 2)维数组
    cells_contours_coord = request_form_to_dict.get('cells_contours_coord', None)

    # 检验参数
    if not image_id or not x or not y or not w or not h or not cells_contours_coord:
        return make_response(jsonify({'msg': '参数错误！'}))
    if not eval(cells_contours_coord):
        return make_response(jsonify({'msg': '参数错误！'}))

    # 将数据转成整数
    try:
        x, y, w, h = int(x), int(y), int(w), int(h)
    except Exception as e:
        return make_response(jsonify({'msg': '参数错误！'}))

    # 根据id, 读取图像
    slide = get_slide(image_id, get_path(image_id))

    # 根据(x,y), w, h切图
    tile_image = slide.read_region((x, y), 0, (w, h))

    # 保存图像
    img_name = './Services/Yolo/detected_img/screenshot_{}.png'.format(2)
    tile_image.save(img_name)
    # 读取图像
    raw_img = cv2.imread(img_name)
    # 删除图像
    os.remove(img_name)

    # 初始化黑色画布, 维度和region的大小一样
    mask_contour = np.zeros((h, w))
    # 轮廓坐标转换维度, 符合cv2的输入
    cells_contours_coord = eval(cells_contours_coord)
    cells_contours_coord_reshape = np.array(cells_contours_coord).reshape(-1, 1, 2)
    # 画出实心轮廓图
    # 先将轮廓在大图上的坐标转换回其在框选区域中的坐标
    cell_contours_coord_region = cells_contours_coord_reshape - np.array([x, y])
    # cv2.drawContours中的第二个参数要是一个列表(列表中有数组，如[numpy.array()])
    cv2.drawContours(mask_contour, [cell_contours_coord_region], 0, color=(255, 255, 255), thickness=-1)

    # 计算细胞轮廓面积和周长
    cells_contours_perimeter = cv2.arcLength(cells_contours_coord_reshape, True)
    cells_contours_area = cv2.contourArea(cells_contours_coord_reshape)

    # 计算灰度值
    # pred为细胞核的坐标值, 需要转换成0-1矩阵, 识别到的地方为1, 没有的为0
    zero_one_matrix = np.where(mask_contour > 0, 1, 0)
    # 图像灰度化处理
    gray_img = cv2.cvtColor(raw_img, cv2.COLOR_RGB2GRAY)
    # 像素重新计算(图像中颜色深的像素的值越接近于0, 越浅的颜色越接近于255,
    # 而在细胞核灰度中, 如果细胞核颜色越深的话, 其灰度值应该越大, 因此需要将其进行颜色值调换)
    gray_img_resort = 255 - gray_img
    cells_contours_gray = np.sum(zero_one_matrix * gray_img_resort)

    # 返回细胞核微调后的信息：周长, 面积, 灰度值
    return make_response(jsonify({
        'cells_contours_gray': int(cells_contours_gray),
        'cells_contours_perimeter': round(cells_contours_perimeter),
        'cells_contours_area': round(cells_contours_area)
    }))


if __name__ == '__main__':

    # 开启日志
    ConfigLog()
    # use_reloader不启动自动更新
    # threaded=False:不启动多线程, 因为使用默认的启动多线程会和mxnet框架有冲突,会报错
    app.run(debug=True, host='192.168.2.179', port=5011, use_reloader=False, threaded=False)
