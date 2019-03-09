# coding=utf-8

from PIL import Image
import os
import sys


# gpu num
# GPU_NUM = len(os.popen("lspci|grep VGA|grep NVIDIA").read().split('\n')) - 1
# GPU_INDEX = tuple(i for i in range(GPU_NUM))
yolo_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(yolo_path)

from darknet.darknet import *


class YoloInterface(object):
    # __instance = None
    #
    # def __new__(cls, *args, **kwargs):
    #     if not cls.__instance:
    #         cls.__instance = super().__new__(cls, *args, **kwargs)
    #     return cls.__instance

    def __init__(self):
        self.net = load_net("{}/config/my_yolo.cfg".format(yolo_path).encode(),
                            "{}/config/my_yolo.backup".format(yolo_path).encode(), 0)
        self.meta = load_meta("{}/config/my_yolo.data".format(yolo_path).encode())

    def _get_yolo_detection_location(self, image_path, thresh):
        '''
        调用yolo接口获的检测结果
        :param image_path: 待检测图像路径
        :param thresh: 设置阈值,获得置信度在阈值之上的结果
        :return: 置信度,以及x,y,w,h的列表
        '''

        rets = detect(self.net, self.meta, image_path.encode(), thresh)
        ret_list = []
        for ret in rets:
            _, det, loc_info = ret
            loc_info = tuple(map(round, loc_info))
            ret_list.append((det, loc_info))
        return ret_list

    def get_detect_img(self, in_path, out_path, thresh=0.5):
        '''
        获取检测图片
        :param in_path: 待检测的图片路径
        :param out_path: 输出图片的路径
        :param thresh: 阈值o
        :return: None
        '''
        file_path = in_path
        if os.path.isdir(in_path):
            file_path = os.listdir(in_path)[0]
        os.makedirs(out_path, exist_ok=True)
        file_name, postfix = os.path.basename(file_path).split('.')
        rets = self._get_yolo_detection_location(file_path, thresh)
        img = Image.open(file_path)
        right, bottom = img.size
        for ret in rets:
            x, y, w, h = ret[1]
            box = (
                x - w // 2 if x - w // 2 > 0 else 0, y - h // 2 if y - h // 2 > 0 else 0,
                x + w // 2 if x + w // 2 < right else right, y + h // 2 if y + h // 2 < bottom else bottom
            )
            new_name = file_name + '_%.4f' % ret[0] + '_x{}_y{}_w{}_h{}.{}'.format(box[0], box[1], box[2] - box[0],
                                                                                   box[3] - box[1], postfix)
            img.crop(box).save(os.path.join(out_path, new_name))
        img.close()


if __name__ == '__main__':

    yolo = YoloInterface()
    while 1:
        yolo.get_detect_img('/home/wqf/桌面/screenshot_1551796474452.png', '/home/wqf/桌面/temp_img')