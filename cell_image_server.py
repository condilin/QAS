# !/usr/bin/env python3
# -*- encoding: utf-8 -*-
# @author: condi
# @file: cell_image_server.py
# @time: 19-2-12 下午3:36

import requests, os, time
import numpy as np
import requests
import logging

from flask import Flask, make_response, jsonify
from flask_cors import CORS

from Services.Aslide.aslide import Aslide
from Services.utils import PaddingTiles
from Services.Yolo.Yolo_Detect.lct_pro_unic import yolo_detect
from Services.Unet.unetImp_comment import segment

app = Flask(__name__)
# 跨域支持
CORS(app)
app.secret_key = 'xfsdfqw'

tif_path_cache = {}
slide_cache = {}

QAS_HOST = '192.168.2.179:8010'
TIF_PATH_PREX = '/run/user/1000/gvfs/smb-share:server=192.168.2.221,share='


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
    img = image_id + '_' + img_name

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

    # cells_coordinate = '_'.join([str(x), str(y), str(w), str(h)])
    #
    print('in ==================> ')
    start_time = time.time()

    # # 根据id, 读取图像
    slide = get_slide(image_id, get_path(image_id))
    # http://192.168.2.179:5000/tiles/1211732/24700/25587/179/165

    # 根据(x,y), w, h切图
    tile_image = slide.read_region((x, y), 0, (w, h))
    # 将图片保存以供yolo进行细胞检测
    current_time = time.strftime("%Y-%m-%d %H:%M:%S")
    # tile_image.save('./Services/Yolo/wait_detect_img/screenshot_{}.png'.format(current_time))
    # # 对用户的截图进行处理(大于608x608=>缩成608x608, 否则padding成608x608)
    # PaddingTiles().padding_tiles(
    #     './Services/Yolo/wait_detect_img/screenshot_{}.png'.format(current_time),
    #     cells_coordinate, current_time, padding_methods='around', padding_border='white'
    # )

    # 加载yolo模型对padding后的图像进行细胞检测
    # yolo_detect('./Services/Yolo/padding_detect_img', './Services/Yolo/detected_img')
    # yolo_detect('/home/kyfq/tmp/tiffs_111111', './Services/Yolo/detected_img')

    # ----- 测试：不经过yolo, 直接使用unet进行预测 ------ #
    tile_image.save('./Services/Yolo/detected_img/screenshot_{}.png'.format(1))

    # 加载unet模型, 获取分割后细胞核信息
    contours_info = segment('./Services/Yolo/detected_img/', './Services/Unet/segmented_img/')

    # 获取真实坐标
    for contour in contours_info:
        # unet输入的小图,得到的坐标
        unet_input_coord = contour['cells_contours_coord']

        # 判断是否检测到细胞, 检测不到则返回None
        if unet_input_coord is not None:
            # 原图的坐标
            raw_img_cord = np.array([x, y])
            # 加上padding后的坐标
            # add = np.array([100, 100])

            # 细胞核真实的坐标 = 细胞核在unet小图中的坐标 + 小图在大图的坐标
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


if __name__ == '__main__':

    # 开启日志
    ConfigLog()

    app.run(debug=True, host='192.168.2.179', port=5011)
