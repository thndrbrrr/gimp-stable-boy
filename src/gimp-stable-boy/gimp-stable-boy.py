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
from time import time as time  #beauty
import base64
import urllib2
import tempfile
import gimpfu
from gimpfu import *

# Fix relative imports in Windows
path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(1, path)
from params import GIMP_PARAMS, IMAGE_TARGETS as IMG_TARGET, SAMPLERS


MASK_LAYER_NAME = 'Inpainting Mask'


def encode_png(img_path):
    with open(img_path, "rb") as img:
        return 'data:image/png;base64,' + base64.b64encode(img.read())


def encode_init_img(src_img, src_drw):
    _, x1, y1, x2, y2 = pdb.gimp_selection_bounds(src_img)
    # print(str(x1) + " " + str(y1) + " " + str(x2) + " " + str(y2))
    img = pdb.gimp_image_duplicate(src_img)
    inp_layer = pdb.gimp_image_get_layer_by_name(img, MASK_LAYER_NAME)
    if inp_layer:
        pdb.gimp_image_remove_layer(img, inp_layer)
    pdb.gimp_image_select_rectangle(img, 2, x1, y1, x2 - x1, y2 - y1)
    pdb.gimp_edit_copy_visible(img)
    sel_img = pdb.gimp_edit_paste_as_new_image()
    tmp_init_img_path = tempfile.mktemp(suffix='.png')
    pdb.file_png_save_defaults(sel_img, sel_img.layers[0], tmp_init_img_path, tmp_init_img_path)
    encoded_init_img = encode_png(tmp_init_img_path)
    print('init img: ' + tmp_init_img_path)
    # os.remove(tmp_init_img_path)
    return encoded_init_img


def encode_mask(src_img, src_drw):
    if not pdb.gimp_image_get_layer_by_name(src_img, MASK_LAYER_NAME):
        raise Exception("Couldn't find layer named '" + MASK_LAYER_NAME + "'")
    _, x1, y1, x2, y2 = pdb.gimp_selection_bounds(src_img)
    img = pdb.gimp_image_duplicate(src_img)
    for layer in img.layers:
        pdb.gimp_item_set_visible(layer, layer.name == MASK_LAYER_NAME)
    pdb.gimp_image_select_rectangle(img, 2, x1, y1, x2 - x1, y2 - y1)
    pdb.gimp_edit_copy_visible(img)
    mask_img = pdb.gimp_edit_paste_as_new_image()
    pdb.gimp_layer_flatten(mask_img.layers[0])

    # inp_layer = pdb.gimp_layer_new_from_drawable(src_inp_layer, mask_img)
    # mask_img = pdb.gimp_image_new(img.width, img.height, 0)
    # pdb.gimp_item_set_visible(inp_layer, True)
    # pdb.gimp_layer_flatten(inp_layer)
    # mask_img.add_layer(inp_layer, 1)
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
        # os.remove(tmp_img_path)


def create_layers(img, drw, img_batch):
    for encoded_sd_img in img_batch:
        with open(tempfile.mktemp(suffix='.png'), 'wb') as tmp_sd_img:
            tmp_sd_img_path = tmp_sd_img.name
            tmp_sd_img.write(base64.b64decode(encoded_sd_img.split(",", 1)[0]))
        sd_img = pdb.file_png_load(tmp_sd_img_path, tmp_sd_img_path)
        sd_drw = pdb.gimp_image_active_drawable(sd_img)
        sd_layer = pdb.gimp_layer_new_from_drawable(sd_drw, img)
        sd_layer.name = 'sd_' + str(int(time()))
        img.add_layer(sd_layer, 0)
        _, x, y, _, _ = pdb.gimp_selection_bounds(img)
        pdb.gimp_layer_set_offsets(sd_layer, x, y)
        pdb.gimp_image_delete(sd_img)
    mask_layer = pdb.gimp_image_get_layer_by_name(img, MASK_LAYER_NAME)
    if mask_layer:
        pdb.gimp_image_raise_item_to_top(img, mask_layer)
        pdb.gimp_item_set_visible(mask_layer, False)


def make_extras_request_data(**kwargs):
    return {
        'upscaling_resize': int(kwargs['upscaling_resize']),
        'image': encode_init_img(kwargs['image'], kwargs['drawable']),
    }


def make_generation_request_data(**kwargs):
    return {
        'prompt': kwargs['prompt'],
        'negative_prompt': kwargs['negative_prompt'],
        'steps': kwargs['steps'],
        'sampler_index': SAMPLERS[kwargs['sampler_index']],
        'batch_size': int(kwargs['num_images']),
        'cfg_scale': kwargs['cfg_scale'],
        'seed': kwargs['seed'],
        'restore_faces': kwargs['restore_faces'],
    }


def add_img2img_params(req_data, **kwargs):
    req_data['denoising_strength'] = float(kwargs['denoising_strength']) / 100
    req_data['init_images'] = [encode_init_img(kwargs['image'], kwargs['drawable'])]
    return req_data


def add_inpainting_params(req_data, **kwargs):
    req_data['inpainting_mask_invert'] = 1
    req_data['inpainting_fill'] = kwargs['inpainting_fill']
    req_data['mask_blur'] = kwargs['mask_blur']
    req_data['inpaint_full_res'] = kwargs['inpaint_full_res']
    req_data['inpaint_full_res_padding'] = kwargs['inpaint_full_res_padding']
    req_data['mask'] = encode_mask(kwargs['image'], kwargs['drawable'])
    return req_data


def create_api_request_from_gimp_params(**kwargs):
    if kwargs['mode'] == 'TXT2IMG':
        uri = 'sdapi/v1/txt2img'
        req_data = make_generation_request_data(**kwargs)
    elif kwargs['mode'] in ['IMG2IMG', 'INPAINTING']:
        uri = 'sdapi/v1/img2img'
        req_data = make_generation_request_data(**kwargs)
        req_data = add_img2img_params(req_data, **kwargs)
        if kwargs['mode'] == 'INPAINTING':
            req_data = add_inpainting_params(req_data, **kwargs)
    elif kwargs['mode'] == 'EXTRAS':
        uri = 'sdapi/v1/extra-single-image'
        req_data = make_extras_request_data(**kwargs)
    url = kwargs['api_base_url'] + ('/' if not kwargs['api_base_url'].endswith('/') else '') + uri
    print(url)
    return urllib2.Request(url=url, headers={'Content-Type': 'application/json'}, data=json.dumps(req_data))


def run(*args, **kwargs):
    img = kwargs['image']
    try:
        sd_request = create_api_request_from_gimp_params(**kwargs)
        print(sd_request.get_full_url())
        # # with open('/var/folders/_g/x2n28ygx3ts8lk5c_16b3rrr0000gn/T/tmpEO5Sw_.png') as png:
        # #     tmp_sd_img = png.read()
        # with open('/private/var/folders/_g/x2n28ygx3ts8lk5c_16b3rrr0000gn/T/tmpYRJ2gI.png', "rb") as img:
        #     # 'data:image/png;base64,' + base64.b64encode(img.read())
        #     # enc_tmp_img = 'data:image/png;base64,' + base64.b64encode(img.read())
        #     enc_tmp_img = base64.b64encode(img.read())
        # print(len(enc_tmp_img))
        # print(enc_tmp_img[:40])
        # create_layers(kwargs['image'], kwargs['drawable'], [enc_tmp_img, enc_tmp_img])
        # return
        sd_result = json.loads(urllib2.urlopen(sd_request).read())
        if kwargs['mode'] == 'EXTRAS':
            generated_images = [sd_result['image']]
        else:
            generated_images = sd_result['images']
        img.undo_group_start()
        if IMG_TARGET[kwargs['img_target']] == 'Images':
            open_as_images(generated_images)
        elif IMG_TARGET[kwargs['img_target']] == 'Layers':
            # TODO: Put layer to right position
            create_layers(kwargs['image'], kwargs['drawable'], generated_images)
        img.undo_group_end()
    except urllib2.HTTPError as e:
        print(e)
        print(e.read())


def run_txt2img(*args, **kwargs):
    kwargs.update(dict(zip((param[1] for param in GIMP_PARAMS['TXT2IMG']), args)))
    kwargs['mode'] = 'TXT2IMG'
    run(args, **kwargs)


def run_img2img(*args, **kwargs):
    kwargs.update(dict(zip((param[1] for param in GIMP_PARAMS['IMG2IMG']), args)))
    kwargs['mode'] = 'IMG2IMG'
    run(args, **kwargs)


def run_inpainting(*args, **kwargs):
    kwargs.update(dict(zip((param[1] for param in GIMP_PARAMS['INPAINTING']), args)))
    kwargs['mode'] = 'INPAINTING'
    run(args, **kwargs)


def run_extras(*args, **kwargs):
    kwargs.update(dict(zip((param[1] for param in GIMP_PARAMS['EXTRAS']), args)))
    kwargs['mode'] = 'EXTRAS'
    kwargs['img_target'] = 1
    run(args, **kwargs)


if __name__ == '__main__':
    gimpfu.register("stable-boy-txt2img", "Stable Boy - Text to Image",
                    "Stable Diffusion plugin that uses AUTOMATIC1111's webgui API", "Torben Giesselmann",
                    "Torben Giesselmann", "2022", "<Image>/Stable Boy/Text to Image", "*", GIMP_PARAMS['TXT2IMG'], [],
                    run_txt2img)
    gimpfu.register("stable-boy-img2img", "Stable Boy - Image to Image",
                    "Stable Diffusion plugin that uses AUTOMATIC1111's webgui API", "Torben Giesselmann",
                    "Torben Giesselmann", "2022", "<Image>/Stable Boy/Image to Image", "*", GIMP_PARAMS['IMG2IMG'], [],
                    run_img2img)
    gimpfu.register("stable-boy-inpaint", "Stable Boy - Inpainting",
                    "Stable Diffusion plugin that uses AUTOMATIC1111's webgui API", "Torben Giesselmann",
                    "Torben Giesselmann", "2022", "<Image>/Stable Boy/Inpainting", "*", GIMP_PARAMS['INPAINTING'], [],
                    run_inpainting)
    gimpfu.register("stable-boy-extras", "Stable Boy - Extras",
                    "Stable Diffusion plugin that uses AUTOMATIC1111's webgui API", "Torben Giesselmann",
                    "Torben Giesselmann", "2022", "<Image>/Stable Boy/Extras", "*", GIMP_PARAMS['EXTRAS'], [],
                    run_extras)
    ssl._create_default_https_context = ssl._create_unverified_context
    gimpfu.main()