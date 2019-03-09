# !/usr/bin/env python3
# -*- encoding: utf-8 -*-
# @author: condi
# @file: tmp4.py
# @time: 19-1-28 下午3:19


import os


class FindNeed(object):

    def __init__(self):
        self.path = '/media/kyfq/f2b5b050-085b-4a49-b06d-f9e7e99e0abd/kyfq/cells_three/FUNGI'
        # self.path = '/media/kyfq/f2b5b050-085b-4a49-b06d-f9e7e99e0abd/kyfq/cells_three/ACTINO'
        self.res_list = {}

    def run(self):
        for pathology in os.listdir(self.path):
            self.res_list.setdefault(pathology, {})
            for cls in os.listdir(os.path.join(self.path, pathology)):
                img_list = os.listdir(os.path.join(self.path, pathology, cls))
                self.res_list[pathology].setdefault(cls, len(img_list))

    def statistic(self):
        for k, v in self.res_list.items():
            if 'HSIL_S' in v and 'LSIL_E' in v and 'ASCUS' in v and 'SC' in v:
                print('pathology: %s' % k,
                      'ASCUS: %s' % v.get('ASCUS'),
                      'LSIL_E: %s' % v.get('LSIL_E'),
                      'HSIL_S: %s' % v.get('HSIL_S'),
                      'SC: %s' % v.get('SC')
                      )


if __name__ == '__main__':
    find_need = FindNeed()
    find_need.run()
    find_need.statistic()

