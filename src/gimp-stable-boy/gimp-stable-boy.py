#!/usr/bin/env python

# Stable Boy
# Copyright (C) 2022 Torben Giesselmann
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os, sys
import ssl
import json
import math
from time import sleep
from time import time as current_time
from time import time as time  #beauty
import base64
import urllib2
import gtk
from threading import Thread
import tempfile
import gimpfu
from gimpfu import *

# Fix relative imports in Windows
path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(1, path)
from params import GIMP_PARAMS, IMAGE_TARGETS as IMG_TARGET, SAMPLERS, UPSCALERS

REQUEST_TIMEOUT_SECONDS = 40

__version__ = '0.3'

MASK_LAYER_NAME = 'Inpainting Mask'

def encode_png(img_path):
    with open(img_path, "rb") as img:
        return 'data:image/png;base64,' + base64.b64encode(img.read())


def autofit_inpainting_area(src_img):
    if not pdb.gimp_image_get_layer_by_name(src_img, MASK_LAYER_NAME):
        raise Exception("Couldn't find layer named '" + MASK_LAYER_NAME + "'")
    img = pdb.gimp_image_duplicate(src_img)
    mask_layer = pdb.gimp_image_get_layer_by_name(img, MASK_LAYER_NAME)
    pdb.plug_in_autocrop_layer(img, mask_layer)
    mask_center_x = mask_layer.offsets[0] + int(mask_layer.width / 2)
    mask_center_y = mask_layer.offsets[1] + int(mask_layer.height / 2)
    target_width = math.ceil(float(mask_layer.width) / 256) * 256
    target_height = math.ceil(float(mask_layer.height) / 256) * 256
    if target_width < 512:
        target_width = 512
    if target_height < 512:
        target_height = 512
    x, y = mask_center_x - target_width / 2, mask_center_y - target_height / 2
    if x + target_width > img.width:
        x = img.width - target_width
    if y + target_height > img.height:
        y = img.height - target_height
    if mask_center_x - target_width / 2 < 0:
        x = 0
    if mask_center_y - target_height / 2 < 0:
        y = 0
    return x, y, target_width, target_height


def determine_active_area(img, autofit_inpainting=False):
    _, x, y, x2, y2 = pdb.gimp_selection_bounds(img)
    width = x2 - x
    height = y2 - y
    # TODO: should an active rectangular selection override autofit?
    if autofit_inpainting:
        x, y, width, height = autofit_inpainting_area(img)
    return x, y, width, height


def encode_init_img(src_img, x, y, width, height):
    img = pdb.gimp_image_duplicate(src_img)
    inp_layer = pdb.gimp_image_get_layer_by_name(img, MASK_LAYER_NAME)
    if inp_layer:
        pdb.gimp_image_remove_layer(img, inp_layer)
    pdb.gimp_image_select_rectangle(img, 2, x, y, width, height)
    pdb.gimp_edit_copy_visible(img)
    sel_img = pdb.gimp_edit_paste_as_new_image()
    tmp_init_img_path = tempfile.mktemp(suffix='.png')
    pdb.file_png_save_defaults(sel_img, sel_img.layers[0], tmp_init_img_path, tmp_init_img_path)
    encoded_init_img = encode_png(tmp_init_img_path)
    print('init img: ' + tmp_init_img_path)
    # os.remove(tmp_init_img_path)
    return encoded_init_img


def encode_mask(src_img, x, y, width, height):
    if not pdb.gimp_image_get_layer_by_name(src_img, MASK_LAYER_NAME):
        raise Exception("Couldn't find layer named '" + MASK_LAYER_NAME + "'")
    img = pdb.gimp_image_duplicate(src_img)
    for layer in img.layers:
        pdb.gimp_item_set_visible(layer, layer.name == MASK_LAYER_NAME)
    pdb.gimp_image_select_rectangle(img, 2, x, y, width, height)
    pdb.gimp_edit_copy_visible(img)
    mask_img = pdb.gimp_edit_paste_as_new_image()
    pdb.gimp_layer_flatten(mask_img.layers[0])
    mask_img_path = tempfile.mktemp(suffix='.png')
    pdb.file_png_save_defaults(mask_img, mask_img.layers[0], mask_img_path, mask_img_path)
    encoded_mask = encode_png(mask_img_path)
    print('mask img: ' + mask_img_path)
    # os.remove(mask_img_path)
    return encoded_mask


def open_as_images(images):
    for img in images:
        with open(tempfile.mktemp(suffix='.png'), 'wb') as tmp_generated_img:
            tmp_img_path = tmp_generated_img.name
            print(tmp_img_path)
            content = base64.b64decode(img.split(",", 1)[0])
            tmp_generated_img.write(content)
        gimp_img = pdb.file_png_load(tmp_img_path, tmp_img_path)
        # TODO: add "Inpainting" layer?
        pdb.gimp_display_new(gimp_img)
        os.remove(tmp_img_path)


def create_layers(img, images, x, y):
    for encoded_sd_img in images:
        with open(tempfile.mktemp(suffix='.png'), 'wb') as tmp_sd_img:
            tmp_sd_img_path = tmp_sd_img.name
            tmp_sd_img.write(base64.b64decode(encoded_sd_img.split(",", 1)[0]))
        sd_img = pdb.file_png_load(tmp_sd_img_path, tmp_sd_img_path)
        sd_drw = pdb.gimp_image_active_drawable(sd_img)
        sd_layer = pdb.gimp_layer_new_from_drawable(sd_drw, img)
        sd_layer.name = 'sd_' + str(int(time()))
        img.add_layer(sd_layer, 0)
        pdb.gimp_layer_set_offsets(sd_layer, x, y)
        pdb.gimp_image_delete(sd_img)
        os.remove(tmp_sd_img_path)
    mask_layer = pdb.gimp_image_get_layer_by_name(img, MASK_LAYER_NAME)
    if mask_layer:
        pdb.gimp_image_raise_item_to_top(img, mask_layer)
        pdb.gimp_item_set_visible(mask_layer, False)


def make_extras_request_data(**kwargs):
    return {
        'upscaling_resize': int(kwargs['upscaling_resize']),
        'upscaler_1': UPSCALERS[kwargs['upscaler_1']],
        'upscaler_2': UPSCALERS[kwargs['upscaler_2']],
        'extras_upscaler_2_visibility': kwargs['extras_upscaler_2_visibility'],
    }


def make_generation_request_data(**kwargs):
    _, x1, y1, x2, y2 = pdb.gimp_selection_bounds(kwargs['image'])
    return {
        'prompt': kwargs['prompt'],
        'negative_prompt': kwargs['negative_prompt'],
        'steps': kwargs['steps'],
        'sampler_index': SAMPLERS[kwargs['sampler_index']],
        'batch_size': int(kwargs['num_images']),
        'cfg_scale': kwargs['cfg_scale'],
        'seed': kwargs['seed'],
        'restore_faces': kwargs['restore_faces'],
        'width': x2 - x1,
        'height': y2 - y1,
    }


def add_img2img_params(req_data, **kwargs):
    req_data['denoising_strength'] = float(kwargs['denoising_strength']) / 100
    return req_data


def add_inpainting_params(req_data, **kwargs):
    req_data['inpainting_mask_invert'] = 1
    req_data['inpainting_fill'] = kwargs['inpainting_fill']
    req_data['mask_blur'] = kwargs['mask_blur']
    req_data['inpaint_full_res'] = kwargs['inpaint_full_res']
    req_data['inpaint_full_res_padding'] = kwargs['inpaint_full_res_padding']
    return req_data

class ApiRequest(Thread):
        def __init__(self, url, req_data):
            Thread.__init__(self)
            self.url = url
            self.req_data = req_data
            self.waiting_request = True

        def run(self):
            try:
                sd_request = urllib2.Request(url=self.url, headers={'Content-Type': 'application/json'}, data=json.dumps(self.req_data))
                sd_response = urllib2.urlopen(sd_request)
                self.data = json.loads(sd_response.read())
                self.waiting_request = False
            except Exception as e:
                gimpfu.gimp.message(str(e))
                gimpfu.gimp.message(str(self.url))
                gimpfu.gimp.message(str(json.dumps(self.req_data)))
                self.request_error = e

def api_request_from_gimp_params(**kwargs):
    if kwargs['mode'] == 'TXT2IMG':
        uri = 'sdapi/v1/txt2img'
        req_data = make_generation_request_data(**kwargs)
    elif kwargs['mode'] in ['IMG2IMG', 'INPAINTING']:
        uri = 'sdapi/v1/img2img'
        req_data = make_generation_request_data(**kwargs)
        req_data = add_img2img_params(req_data, **kwargs)
        req_data['init_images'] = [
            encode_init_img(kwargs['image'], kwargs['x'], kwargs['y'], kwargs['width'], kwargs['height'])
        ]
        if kwargs['mode'] == 'INPAINTING':
            req_data = add_inpainting_params(req_data, **kwargs)
            req_data['mask'] = encode_mask(kwargs['image'], kwargs['x'], kwargs['y'], kwargs['width'], kwargs['height'])
    elif kwargs['mode'] == 'EXTRAS':
        uri = 'sdapi/v1/extra-single-image'
        req_data = make_extras_request_data(**kwargs)
        req_data['image'] = encode_init_img(kwargs['image'], kwargs['x'], kwargs['y'], kwargs['width'],
                                            kwargs['height'])
                                            
    url = kwargs['api_base_url'] + ('/' if not kwargs['api_base_url'].endswith('/') else '') + uri
    print(url)

    t = ApiRequest(url, req_data)
    t.start()
    request_start_time = current_time()
    while t.waiting_request:
        sleep(2)
        time_spent = current_time() - request_start_time
        percent_time_spent_until_timeout = time_spent / REQUEST_TIMEOUT_SECONDS
        gimp.progress_update(percent_time_spent_until_timeout)
        if time_spent > REQUEST_TIMEOUT_SECONDS:
            raise Exception('Timeout waiting server.')

    t.join()
    if hasattr(t, 'request_error'):
        raise t.request_error
    return t.data


def run(*args, **kwargs):
    img = kwargs['image']
    try:
        x, y, width, height = determine_active_area(kwargs['image'], kwargs['autofit_inpainting'])
        gimp.progress_init('Waiting for server')
        sd_result = api_request_from_gimp_params(x=x, y=y, width=width, height=height, **kwargs)
        
        if kwargs['mode'] == 'EXTRAS':
            generated_images = [sd_result['image']]
        else:
            generated_images = sd_result['images']
        img.undo_group_start()
        if IMG_TARGET[kwargs['img_target']] == 'Images':
            open_as_images(generated_images)
        elif IMG_TARGET[kwargs['img_target']] == 'Layers':
            create_layers(kwargs['image'], generated_images, x, y)
        img.undo_group_end()
        gimp.progress_update(100)
    except Exception as e:
        gimp.progress_update(0)
        print(e)
        gimpfu.gimp.message(str(e)) # Show message on error console
        dialog = gtk.MessageDialog(
            None,
            gtk.DIALOG_MODAL,
            gtk.MESSAGE_INFO,
            gtk.BUTTONS_OK,
            str(e),
        )

        # Display the dialog and wait for the user to dismiss it
        response = dialog.run()
        return


def run_txt2img(*args, **kwargs):
    kwargs.update(dict(zip((param[1] for param in GIMP_PARAMS['TXT2IMG']), args)))
    kwargs['mode'] = 'TXT2IMG'
    kwargs['autofit_inpainting'] = False
    run(args, **kwargs)


def run_img2img(*args, **kwargs):
    kwargs.update(dict(zip((param[1] for param in GIMP_PARAMS['IMG2IMG']), args)))
    kwargs['mode'] = 'IMG2IMG'
    kwargs['autofit_inpainting'] = False
    run(args, **kwargs)


def run_inpainting(*args, **kwargs):
    kwargs.update(dict(zip((param[1] for param in GIMP_PARAMS['INPAINTING']), args)))
    kwargs['mode'] = 'INPAINTING'
    run(args, **kwargs)


def run_extras(*args, **kwargs):
    kwargs.update(dict(zip((param[1] for param in GIMP_PARAMS['EXTRAS']), args)))
    kwargs['mode'] = 'EXTRAS'
    kwargs['img_target'] = 1
    kwargs['autofit_inpainting'] = False
    run(args, **kwargs)


if __name__ == '__main__':
    gimpfu.register("stable-boy-txt2img", "Stable Boy " + __version__ + " - Text to Image",
                    "Stable Diffusion plugin for AUTOMATIC1111's WebUI API", "Torben Giesselmann", "Torben Giesselmann",
                    "2022", "<Image>/Stable Boy/Text to Image", "*", GIMP_PARAMS['TXT2IMG'], [], run_txt2img)
    gimpfu.register("stable-boy-img2img", "Stable Boy " + __version__ + " - Image to Image",
                    "Stable Diffusion plugin for AUTOMATIC1111's WebUI API", "Torben Giesselmann", "Torben Giesselmann",
                    "2022", "<Image>/Stable Boy/Image to Image", "*", GIMP_PARAMS['IMG2IMG'], [], run_img2img)
    gimpfu.register("stable-boy-inpaint", "Stable Boy " + __version__ + " - Inpainting",
                    "Stable Diffusion plugin for AUTOMATIC1111's WebUI API", "Torben Giesselmann", "Torben Giesselmann",
                    "2022", "<Image>/Stable Boy/Inpainting", "*", GIMP_PARAMS['INPAINTING'], [], run_inpainting)
    gimpfu.register("stable-boy-extras", "Stable Boy " + __version__ + " - Extras",
                    "Stable Diffusion plugin for AUTOMATIC1111's WebUI API", "Torben Giesselmann", "Torben Giesselmann",
                    "2022", "<Image>/Stable Boy/Extras", "*", GIMP_PARAMS['EXTRAS'], [], run_extras)
    ssl._create_default_https_context = ssl._create_unverified_context
    gimpfu.main()