import os
import tempfile
from gimpfu import *
from gimpshelf import shelf
import constants
import base64


def save_prefs(group_name, **kwargs):
    for pref_key in (key for key in kwargs.keys() if key not in ['image', 'drawable']):
        shelf[group_name + '_' + pref_key] = kwargs[pref_key]

def pref_value(group_name, key_name, default=None):
    full_key = group_name + '_' + key_name
    return shelf[full_key] if shelf.has_key(full_key) else default

def encode_png(img_path):
    with open(img_path, "rb") as img:
        return 'data:image/png;base64,' + str(base64.b64encode(img.read()))

def encode_img(img, x, y, width, height):
    img_cpy = pdb.gimp_image_duplicate(img)
    inp_layer = pdb.gimp_image_get_layer_by_name(img_cpy, constants.MASK_LAYER_NAME)
    if inp_layer:
        pdb.gimp_image_remove_layer(img_cpy, inp_layer)
    pdb.gimp_image_select_rectangle(img_cpy, 2, x, y, width, height)
    pdb.gimp_edit_copy_visible(img_cpy)
    img_flat = pdb.gimp_edit_paste_as_new_image()
    img_flat_path = tempfile.mktemp(suffix='.png')
    pdb.file_png_save_defaults(img_flat, img_flat.layers[0], img_flat_path, img_flat_path)
    encoded_img = encode_png(img_flat_path)
    # print('init img: ' + img_flat_path)
    os.remove(img_flat_path)
    return encoded_img

def active_area(img):
    _, x, y, x2, y2 = pdb.gimp_selection_bounds(img)
    return x, y, x2 - x, y2 - y

def autofit_inpainting_area(img):
    if not pdb.gimp_image_get_layer_by_name(img, constants.MASK_LAYER_NAME):
        raise Exception("Couldn't find layer named '" + constants.MASK_LAYER_NAME + "'")
    img_cpy = pdb.gimp_image_duplicate(img)
    mask_layer = pdb.gimp_image_get_layer_by_name(img_cpy, constants.MASK_LAYER_NAME)
    pdb.gimp_image_set_active_layer(img_cpy, mask_layer)  # need to make it the active layer ...
    pdb.plug_in_autocrop_layer(img_cpy, mask_layer)  # ... because this unintuitively crops the active layer (!)
    target_width = math.ceil(float(mask_layer.width) / 256) * 256
    target_width = max(512, target_width)
    target_height = math.ceil(float(mask_layer.height) / 256) * 256
    target_height = max(512, target_height)
    mask_center_x = mask_layer.offsets[0] + int(mask_layer.width / 2)
    mask_center_y = mask_layer.offsets[1] + int(mask_layer.height / 2)
    x, y = mask_center_x - target_width / 2, mask_center_y - target_height / 2
    if x + target_width > img_cpy.width:
        x = img_cpy.width - target_width
    if y + target_height > img_cpy.height:
        y = img_cpy.height - target_height
    if mask_center_x - target_width / 2 < 0:
        x = 0
    if mask_center_y - target_height / 2 < 0:
        y = 0
    return x, y, target_width, target_height

def encode_mask(img, x, y, width, height):
    if not pdb.gimp_image_get_layer_by_name(img, constants.MASK_LAYER_NAME):
        raise Exception("Couldn't find layer named '" + constants.MASK_LAYER_NAME + "'")
    img_cpy = pdb.gimp_image_duplicate(img)
    for layer in img_cpy.layers:
        pdb.gimp_item_set_visible(layer, layer.name == constants.MASK_LAYER_NAME)
    pdb.gimp_image_select_rectangle(img_cpy, 2, x, y, width, height)
    pdb.gimp_edit_copy_visible(img_cpy)
    mask_img = pdb.gimp_edit_paste_as_new_image()
    pdb.gimp_layer_flatten(mask_img.layers[0])
    mask_img_path = tempfile.mktemp(suffix='.png')
    pdb.file_png_save_defaults(mask_img, mask_img.layers[0], mask_img_path, mask_img_path)
    encoded_mask = encode_png(mask_img_path)
    # print('mask img: ' + mask_img_path)
    os.remove(mask_img_path)
    return encoded_mask

def decode_png(encoded_png):
    with open(tempfile.mktemp(suffix='.png'), 'wb') as png_img:
        png_img_path = png_img.name
        png_img.write(base64.b64decode(encoded_png.split(",", 1)[0]))
        return png_img_path

def open_images(images):
    if not images:
        return
    for encoded_img in images:
        tmp_png_path = decode_png(encoded_img)
        img = pdb.file_png_load(tmp_png_path, tmp_png_path)
        pdb.gimp_display_new(img)
        os.remove(tmp_png_path)

def create_layers(img, layers, x, y):
    if not layers:
        return

    def _create_nested_layers(parent_layer, layers):
        for layer in layers:
            if layer.children:
                gimp_layer_group = pdb.gimp_layer_group_new(img)
                gimp_layer_group.name = layer.name
                pdb.gimp_image_insert_layer(img, gimp_layer_group, parent_layer, 0)
                _create_nested_layers(gimp_layer_group, layer.children)
            elif layer.img:
                tmp_png_path = decode_png(layer.img)
                png_img = pdb.file_png_load(tmp_png_path, tmp_png_path)
                gimp_layer = pdb.gimp_layer_new_from_drawable(png_img.layers[0], img)
                gimp_layer.name = layer.name
                pdb.gimp_layer_set_offsets(gimp_layer, x, y)
                pdb.gimp_image_insert_layer(img, gimp_layer, parent_layer, 0)
                pdb.gimp_image_delete(png_img)
                os.remove(tmp_png_path)

    _create_nested_layers(None, layers)
    mask_layer = pdb.gimp_image_get_layer_by_name(img, constants.MASK_LAYER_NAME)
    if mask_layer:
        pdb.gimp_image_raise_item_to_top(img, mask_layer)
        pdb.gimp_item_set_visible(mask_layer, False)