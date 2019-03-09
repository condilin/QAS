# -*- coding: utf8 -*-

import os

import cv2
import numpy as np
import mxnet as mx
from collections import namedtuple


'''
    prefix : prefix of model name  
    epoch : number of iterations of the model. model name = prefix + '-' + epoch + '.params'
    
    seg_data_shape : initialize the network with input shape
    batch_size : batch size
    ctx : select gpu (mx.gpu(0))
    
    return : the Unet model
'''
def get_segmentation_mod(prefix = './segnet_bb5_final', epoch = 0, seg_data_shape = 128, batch_size = 1, ctx = mx.gpu(0)):

    sym, arg_params, aux_params = mx.model.load_checkpoint(prefix, epoch)
    mod = mx.mod.Module(symbol=sym, context=ctx, data_names=['data'], label_names=None)
    mod.bind(for_training=False, data_shapes=[('data', (batch_size, 3, seg_data_shape, seg_data_shape))], label_shapes=None)
    mod.set_params(arg_params=arg_params, aux_params=aux_params)
    return mod


'''
    img : input original image 
    mod : Unet model
    return : predicted results
'''
def seg_img(img, mod):
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

'''
    pred : predicted results from seg_img()
'''
def find_max_contour(pred):
    img3, contours, hierarchy = cv2.findContours(pred, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    mask_contour = np.zeros_like(pred)
    try:
        cv2.drawContours(mask_contour, contours, 0, color=255, thickness=-1)
        return mask_contour, contours
    except:
        return pred, contours

''' 
    img : original image
    a :  coefficient a, img * a + b
    b :  coefficient b, img * a + b
    return :  contrast enhanced  image  
'''
def contrast_brightness_image(img, a = 1.8, b = -90):
    h, w, ch = img.shape
    src2 = np.zeros([h, w, ch], img.dtype)
    dst = cv2.addWeighted(img, a, src2, 1-a, b) 
    return dst


if __name__ == "__main__":
    testdir = r'./data/test'
    savedir = r'./test/'
    imgfiles = [i for i in os.listdir(testdir) if i.endswith('.jpg')]

    seg_mod = get_segmentation_mod()
    print("done")
    for i, fn in enumerate(imgfiles):

        fn_path = testdir+'/'+fn
        raw_img = cv2.imread(fn_path)
        raw_img2 = contrast_brightness_image(raw_img)
#        cv2.imwrite('./' + fn, raw_img)
        pred = seg_img(raw_img2, seg_mod).astype(np.uint8)

        pred, contours = find_max_contour(pred)

        cv2.imwrite(savedir + fn.split('.')[0] + '.png', pred)
        print('save image')

        cv2.drawContours(raw_img, contours, 0, color=(0,255,0), thickness=1)
        cv2.imwrite('/home/kyfq/Desktop/raw_img.png', raw_img)
        cv2.imshow('origin', raw_img)
        cv2.waitKey(0)  # waitkey代表读取键盘的输入，括号里的数字代表等待多长时间，单位ms。 0代表一直等待


# ASCUS   LSIL_E HSIL_S与SC的比值
