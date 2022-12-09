#!/usr/bin/env python
#
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
from time import time as time, sleep  #beauty
from threading import Thread
import base64
from urllib2 import Request, urlopen, URLError
from httplib import HTTPException
import tempfile
import gtk
import gimpfu
from gimpfu import *
from gimpshelf import shelf

# Fix relative imports in Windows
path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(1, path)
from gimp_params import GIMP_PARAMS, IMAGE_TARGETS as IMG_TARGET, SAMPLERS, UPSCALERS


__version__ = '0.3.3'

TIMEOUT_FACTOR = 1
MASK_LAYER_NAME = 'Inpainting Mask'


class StableDiffusionCommand(Thread):
    uri = ''
    status = 'INITIALIZED'

    def __init__(self, **kwargs):
        Thread.__init__(self)
        self.img = kwargs['image']
        self.x, self.y, self.width, self.height = self._determine_active_area()
        print('x, y, w, h: ' + str(self.x) + ', ' + str(self.y) + ', ' + str(self.width) + ', ' + str(self.height))
        self.req_data = self._make_request_data(**kwargs)
        self.timeout = self._estimate_timeout(self.req_data)
        # assert (shelf.has_key['api_base_url'])
        # self.url = shelf['api_base_url'] + ('/' if not shelf['api_base_url'].endswith('/') else '') + self.uri

    def run(self):
        self.status = 'RUNNING'
        try:
            sd_request = Request(url=self.url,
                                 headers={'Content-Type': 'application/json'},
                                 data=json.dumps(self.req_data))
            self.sd_resp = urlopen(sd_request, timeout=self.timeout)
            self._process_http_response(self.sd_resp)
            self.status = 'DONE'
        except HTTPException as e:
            self.status = 'ERROR'
            self.error_msg = str(e)
        except URLError as e:
            self.status = 'ERROR'
            self.error_msg = e.reason

    def _process_http_response(self, resp):
        self.images = json.loads(resp.read())['images']

    def _determine_active_area(self):
        _, x, y, x2, y2 = pdb.gimp_selection_bounds(self.img)
        return x, y, x2 - x, y2 - y

    def _make_request_data(self, **kwargs):
        return {
            'prompt': kwargs['prompt'],
            'negative_prompt': kwargs['negative_prompt'],
            'steps': kwargs['steps'],
            'sampler_index': SAMPLERS[kwargs['sampler_index']],
            'batch_size': int(kwargs['num_images']),
            'cfg_scale': kwargs['cfg_scale'],
            'seed': kwargs['seed'],
            'restore_faces': kwargs['restore_faces'],
            'width': self.width,
            'height': self.height,
        }

    def _estimate_timeout(self, req_data):
        timeout = int(int(req_data['steps']) * int(req_data['batch_size']) * TIMEOUT_FACTOR)
        if req_data['restore_faces']:
            timeout = int(timeout * 1.2 * TIMEOUT_FACTOR)
        return timeout

    def _encode_img(self):
        img_cpy = pdb.gimp_image_duplicate(self.img)
        inp_layer = pdb.gimp_image_get_layer_by_name(img_cpy, MASK_LAYER_NAME)
        if inp_layer:
            pdb.gimp_image_remove_layer(img_cpy, inp_layer)
        pdb.gimp_image_select_rectangle(img_cpy, 2, self.x, self.y, self.width, self.height)
        pdb.gimp_edit_copy_visible(img_cpy)
        img_flat = pdb.gimp_edit_paste_as_new_image()
        img_flat_path = tempfile.mktemp(suffix='.png')
        pdb.file_png_save_defaults(img_flat, img_flat.layers[0], img_flat_path, img_flat_path)
        encoded_img = self.encode_png(img_flat_path)
        print('init img: ' + img_flat_path)
        # os.remove(tmp_init_img_path)
        return encoded_img

    def encode_png(self, img_path):
        with open(img_path, "rb") as img:
            return 'data:image/png;base64,' + base64.b64encode(img.read())


class Txt2ImgCommand(StableDiffusionCommand):
    uri = 'sdapi/v1/txt2img'


class Txt2ImgScriptCommand(StableDiffusionCommand):
    uri = 'sdapi/v1/txt2img/script'

    def _make_request_data(self, **kwargs):
        req_data = StableDiffusionCommand._make_request_data(self, **kwargs)
        req_data['script_name'] = 'X/Y plot'
        req_data['script_args'] = []
        return req_data


class Img2ImgCommand(StableDiffusionCommand):
    uri = 'sdapi/v1/img2img'

    def _make_request_data(self, **kwargs):
        req_data = StableDiffusionCommand._make_request_data(self, **kwargs)
        req_data['denoising_strength'] = float(kwargs['denoising_strength']) / 100
        req_data['init_images'] = [self._encode_img()]
        return req_data


class InpaintingCommand(Img2ImgCommand):
    uri = 'sdapi/v1/img2img'

    def __init__(self, **kwargs):
        self.autofit_inpainting = kwargs['autofit_inpainting']
        Img2ImgCommand.__init__(self, **kwargs)

    def _make_request_data(self, **kwargs):
        req_data = Img2ImgCommand._make_request_data(self, **kwargs)
        req_data['inpainting_mask_invert'] = 1
        req_data['inpainting_fill'] = kwargs['inpainting_fill']
        req_data['mask_blur'] = kwargs['mask_blur']
        req_data['inpaint_full_res'] = kwargs['inpaint_full_res']
        req_data['inpaint_full_res_padding'] = kwargs['inpaint_full_res_padding']
        req_data['mask'] = self.encode_mask()
        return req_data

    def _determine_active_area(self):
        if self.autofit_inpainting:
            return self._autofit_inpainting_area(self.img)
        else:
            return StableDiffusionCommand._determine_active_area(self)

    def _autofit_inpainting_area(self, src_img):
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

    def encode_mask(self):
        if not pdb.gimp_image_get_layer_by_name(self.img, MASK_LAYER_NAME):
            raise Exception("Couldn't find layer named '" + MASK_LAYER_NAME + "'")
        img_cpy = pdb.gimp_image_duplicate(self.img)
        for layer in img_cpy.layers:
            pdb.gimp_item_set_visible(layer, layer.name == MASK_LAYER_NAME)
        pdb.gimp_image_select_rectangle(img_cpy, 2, self.x, self.y, self.width, self.height)
        pdb.gimp_edit_copy_visible(img_cpy)
        mask_img = pdb.gimp_edit_paste_as_new_image()
        pdb.gimp_layer_flatten(mask_img.layers[0])
        mask_img_path = tempfile.mktemp(suffix='.png')
        pdb.file_png_save_defaults(mask_img, mask_img.layers[0], mask_img_path, mask_img_path)
        encoded_mask = self.encode_png(mask_img_path)
        print('mask img: ' + mask_img_path)
        # os.remove(mask_img_path)
        return encoded_mask


class ExtrasCommand(StableDiffusionCommand):
    uri = 'sdapi/v1/extra-single-image'

    def _make_request_data(self, **kwargs):
        return {
            'upscaling_resize': int(kwargs['upscaling_resize']),
            'upscaler_1': UPSCALERS[kwargs['upscaler_1']],
            'upscaler_2': UPSCALERS[kwargs['upscaler_2']],
            'extras_upscaler_2_visibility': kwargs['extras_upscaler_2_visibility'],
            'image': self._encode_img(),
        }

    def _estimate_timeout(self, req_data):
        return (60 if float(req_data['extras_upscaler_2_visibility']) > 0 else 30) * TIMEOUT_FACTOR

    def _process_http_response(self, resp):
        self.images = [json.loads(resp.read())['image']]


########################################################################################################################


def decode_png(encoded_png):
    with open(tempfile.mktemp(suffix='.png'), 'wb') as png_img:
        png_img_path = png_img.name
        png_img.write(base64.b64decode(encoded_png.split(",", 1)[0]))
        return png_img_path


def open_as_images(images):
    for encoded_img in images:
        tmp_png_path = decode_png(encoded_img)
        img = pdb.file_png_load(tmp_png_path, tmp_png_path)
        pdb.gimp_display_new(img)
        os.remove(tmp_png_path)


def create_layers(target_img, images, x, y):
    for encoded_img in images:
        tmp_png_path = decode_png(encoded_img)
        img = pdb.file_png_load(tmp_png_path, tmp_png_path)
        lyr = pdb.gimp_layer_new_from_drawable(img.layers[0], target_img)
        lyr.name = 'sd_' + str(int(time()))
        target_img.add_layer(lyr, 0)
        pdb.gimp_layer_set_offsets(lyr, x, y)
        pdb.gimp_image_delete(img)
        os.remove(tmp_png_path)
    mask_layer = pdb.gimp_image_get_layer_by_name(target_img, MASK_LAYER_NAME)
    if mask_layer:
        pdb.gimp_image_raise_item_to_top(target_img, mask_layer)
        pdb.gimp_item_set_visible(mask_layer, False)


def run(cmd, img_target):
    if not shelf.has_key('api_base_url'):
        dialog = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK,
                                   "Please set API URL in Stable Boy's Preferences.")
        dialog.run()
        return
    else:
        cmd.url = shelf['api_base_url'] + ('/' if not shelf['api_base_url'].endswith('/') else '') + cmd.uri
    try:
        gimp.progress_init('Processing ...')
        request_start_time = time()
        cmd.start()
        while cmd.status == 'RUNNING':
            sleep(1)
            time_spent = time() - request_start_time
            gimp.progress_update(time_spent / float(cmd.timeout))
            if time_spent > cmd.timeout:
                raise Exception('Timed out waiting for response')
        gimp.progress_update(100)
        if cmd.status == 'DONE':
            cmd.join()
            cmd.img.undo_group_start()
            if img_target == 'Images':
                open_as_images(cmd.images)
            elif img_target == 'Layers':
                create_layers(cmd.img, cmd.images, cmd.x, cmd.y)
            cmd.img.undo_group_end()
        elif cmd.status == 'ERROR':
            raise Exception(cmd.error_msg)
    except Exception as e:
        print(e)
        dialog = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, str(e))
        dialog.run()


def run_prefs(*args, **kwargs):
    kwargs.update(dict(zip((param[1] for param in GIMP_PARAMS['PREFERENCES']), args)))
    for pref_key, pref_value in kwargs.items():
        shelf[pref_key] = pref_value


def run_txt2img(*args, **kwargs):
    kwargs.update(dict(zip((param[1] for param in GIMP_PARAMS['TXT2IMG']), args)))
    run(Txt2ImgCommand(**kwargs), img_target=IMG_TARGET[kwargs['img_target']])


def run_img2img(*args, **kwargs):
    kwargs.update(dict(zip((param[1] for param in GIMP_PARAMS['IMG2IMG']), args)))
    run(Img2ImgCommand(**kwargs), img_target=IMG_TARGET[kwargs['img_target']])


def run_inpainting(*args, **kwargs):
    kwargs.update(dict(zip((param[1] for param in GIMP_PARAMS['INPAINTING']), args)))
    run(InpaintingCommand(**kwargs), img_target=IMG_TARGET[kwargs['img_target']])


def run_upscale(*args, **kwargs):
    kwargs.update(dict(zip((param[1] for param in GIMP_PARAMS['UPSCALE']), args)))
    run(ExtrasCommand(**kwargs), img_target='Images')


def run_txt2img_script_xy_plot(*args, **kwargs):
    kwargs.update(dict(zip((param[1] for param in GIMP_PARAMS['SCRIPT_XY_PLOT']), args)))
    run(ExtrasCommand(**kwargs), img_target='Images')


if __name__ == '__main__':
    gimpfu.register("stable-boy-prefs", "Stable Boy " + __version__ + " - Preferences",
                    "Stable Diffusion plugin for AUTOMATIC1111's WebUI API", "Torben Giesselmann", "Torben Giesselmann",
                    "2022", "<Image>/Stable Boy/Preferences", "*", GIMP_PARAMS['PREFERENCES'], [], run_prefs)
    gimpfu.register("stable-boy-txt2img", "Stable Boy " + __version__ + " - Text to Image",
                    "Stable Diffusion plugin for AUTOMATIC1111's WebUI API", "Torben Giesselmann", "Torben Giesselmann",
                    "2022", "<Image>/Stable Boy/Text to Image", "*", GIMP_PARAMS['TXT2IMG'], [], run_txt2img)
    gimpfu.register("stable-boy-img2img", "Stable Boy " + __version__ + " - Image to Image",
                    "Stable Diffusion plugin for AUTOMATIC1111's WebUI API", "Torben Giesselmann", "Torben Giesselmann",
                    "2022", "<Image>/Stable Boy/Image to Image", "*", GIMP_PARAMS['IMG2IMG'], [], run_img2img)
    gimpfu.register("stable-boy-inpaint", "Stable Boy " + __version__ + " - Inpainting",
                    "Stable Diffusion plugin for AUTOMATIC1111's WebUI API", "Torben Giesselmann", "Torben Giesselmann",
                    "2022", "<Image>/Stable Boy/Inpainting", "*", GIMP_PARAMS['INPAINTING'], [], run_inpainting)
    gimpfu.register("stable-boy-upscale", "Stable Boy " + __version__ + " - Upscale",
                    "Stable Diffusion plugin for AUTOMATIC1111's WebUI API", "Torben Giesselmann", "Torben Giesselmann",
                    "2022", "<Image>/Stable Boy/Upscale", "*", GIMP_PARAMS['UPSCALE'], [], run_upscale)
    gimpfu.register("stable-boy-txt2img-script", "Stable Boy " + __version__ + " - Text to Image Script",
                    "Stable Diffusion plugin for AUTOMATIC1111's WebUI API", "Torben Giesselmann", "Torben Giesselmann",
                    "2022", "<Image>/Stable Boy/Scripts/Text to Image/X\/Y plot", "*", GIMP_PARAMS['SCRIPT_XY_PLOT'],
                    [], run_txt2img_script_xy_plot)

    ssl._create_default_https_context = ssl._create_unverified_context
    gimpfu.main()