# -*- coding: utf8 -*-

import os, sys
import requests
import logging
from io import BytesIO

from sanic import Sanic, response
from sanic_cors import CORS
from sanic.response import text, json

from Services.Aslide.aslide import Aslide
from Services.Aslide.deepzoom import ADeepZoomGenerator


app = Sanic(__name__)
# 跨域
CORS(app)

tif_path_cache = {}
slide_cache = {}

QAS_HOST = '192.168.2.179:8010'
TIF_PATH_PREX = '/run/user/1000/gvfs/smb-share:server=192.168.2.221,share='


# 配置日志/初始化变量
class ConfigLog(object):
    def __init__(self):
        # 日志输出的位置
        self.log_name = '/home/kyfq/MyPython/PycharmProjects/qas/QAS/QAS/logs/tiles_server.log'
        # 输出格式
        self.log_format = '%(levelname)s [%(asctime)s] %(message)s'

        # logging配置
        logging.basicConfig(
            level=logging.WARNING,
            format=self.log_format,
            filename=self.log_name,
        )


def get_path(image_id, request):
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
        logging.error('获取图像路径失败：%s' % e)


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
        logging.error('读取图像失败：%s' % e)


@app.route('/tiles/<image_id>/')
async def tiles_dzi(request, image_id):
    """
    get tiff information
    :param request:
    :param image_id: id of tiff image
    :return:
    """

    slide = get_slide(image_id, get_path(image_id, request))

    try:
        zoomer = ADeepZoomGenerator(slide).get_dzi('jpeg')
        return response.html(zoomer)
    except Exception as e:
        return response.html(str(e))


@app.route('/tiles/label_image/<image_id>_label.<format:[A-z]+>')
async def label_image(request, image_id, format):
    """
    get tile image
    :param request:
    :param image_id: id of tiff image
    :param format: view format
    :return:
    """

    slide = get_slide(image_id, get_path(image_id, request))
    bio = BytesIO()
    label_image = slide.label_image
    # 如果标签存在则保存,否则返回一个空字节
    if label_image:
        label_image.save(bio, 'png')
        image_bytes = bio.getvalue()
    else:
        image_bytes = b''

    headers = {}
    headers.setdefault(
        'Content-Disposition',
        'attachment; image_id="{}"'.format(os.path.basename(image_id))
    )

    return response.HTTPResponse(status=200, headers=headers,
                                 body_bytes=image_bytes, content_type='image/png')


@app.route('/tiles/<image_id>_files/<z:int>/<x:int>_<y:int>.<format:[A-z]+>')
async def tiles_png(request, image_id, z, x, y, format):
    """
    get tile image
    :param request:
    :param image_id: id of tiff image
    :param x: coordinate-x
    :param y: coordinate-y
    :param format: view format
    :return:
    """

    slide = get_slide(image_id, get_path(image_id, request))

    x = int(x)
    y = int(y)
    z = int(z)

    bio = BytesIO()
    tiles_image = ADeepZoomGenerator(slide).get_tile(z, (x, y))
    tiles_image.save(bio, 'png')
    image_bytes = bio.getvalue()

    headers = {}
    headers.setdefault(
        'Content-Disposition',
        'attachment; image_id="{}"'.format(os.path.basename(image_id))
    )

    return response.HTTPResponse(status=200, headers=headers,
                                 body_bytes=image_bytes, content_type='image/png')


@app.route("/tiles/screenshots/<image_id>/<x:int>_<y:int>_<w:int>_<h:int>.<format:[A-z]+>")
async def cell_image_request(request, image_id, x, y, w, h, format):
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
    print('==============> in')
    slide = get_slide(image_id, get_path(image_id, request))

    tile_image = slide.read_region((x, y), 0, (w, h))

    bio = BytesIO()

    tile_image.save(bio, 'png')
    image_bytes = bio.getvalue()

    headers = {}
    headers.setdefault(
        'Content-Disposition',
        'attachment; image_id="{}"'.format(os.path.basename(image_id))
    )

    return response.HTTPResponse(status=200, headers=headers,
                                 body_bytes=image_bytes, content_type='image/png')


if __name__ == '__main__':

    # 开启日志
    ConfigLog()

    # access_log=False 不记录成功的日志, error_log=True, 记录失败的日志
    app.run(host='192.168.2.179', port=5010, access_log=False, error_log=True)
    # port = sys.argv[1]
    # try:
    #     port = int(port)
    # except:
    #     raise Exception("PORT %s IS NOT ACCEPTED!" % port)
    #
    # app.run(host="0.0.0.0", port=port, access_log=True, error_log=True)
