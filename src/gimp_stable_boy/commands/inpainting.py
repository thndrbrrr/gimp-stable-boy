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

import gimpfu
import gimp_stable_boy as sb
from image_to_image import Img2ImgCommand
from _command import StableBoyCommand, StableDiffusionCommand

class InpaintingCommand(Img2ImgCommand):
    uri = 'sdapi/v1/img2img'
    metadata = StableBoyCommand.CommandMetadata("stable-boy-inpaint", "Stable Boy " + sb.__version__ + " - Inpainting",
                    "Stable Diffusion plugin for AUTOMATIC1111's WebUI API", "Torben Giesselmann", "Torben Giesselmann",
                    "2022", "<Image>/Stable Boy/Inpainting", "*", [
                        (gimpfu.PF_STRING, 'prompt', 'Prompt', ''),
                        (gimpfu.PF_STRING, 'negative_prompt', 'Negative prompt', ''),
                        (gimpfu.PF_STRING, 'seed', 'Seed', '-1'),
                        (gimpfu.PF_SLIDER, 'steps', 'Steps', 25, (1, 150, 25)),
                        (gimpfu.PF_OPTION, 'sampler_index', 'Sampler', 0, sb.constants.SAMPLERS),
                        (gimpfu.PF_BOOL, 'restore_faces', 'Restore faces', False),
                        (gimpfu.PF_SLIDER, 'cfg_scale', 'CFG', 7.5, (0, 20, 0.5)),
                        (gimpfu.PF_SLIDER, 'denoising_strength', 'Denoising strength %', 50.0, (0, 100, 1)),
                        (gimpfu.PF_BOOL, 'autofit_inpainting', 'Autofit inpainting region', True),
                        (gimpfu.PF_SLIDER, 'mask_blur', 'Mask blur', 4, (0, 32, 1)),
                        (gimpfu.PF_OPTION, 'inpainting_fill', 'Inpainting fill', 1, sb.constants.INPAINTING_FILL_MODE),
                        (gimpfu.PF_BOOL, 'inpaint_full_res', 'Inpaint at full resolution', True),
                        (gimpfu.PF_INT, 'inpaint_full_res_padding', 'Full res. inpainting padding', 0),
                        (gimpfu.PF_SLIDER, 'num_images', 'Number of images', 1, (1, 4, 1)),
                        (gimpfu.PF_OPTION, 'img_target', 'Results as', 0, sb.constants.IMAGE_TARGETS),
                    ], [])

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
        req_data['mask'] = sb.gimp.encode_mask(self.img, self.x, self.y, self.width, self.height)
        return req_data

    def _determine_active_area(self):
        if self.autofit_inpainting:
            return sb.gimp.autofit_inpainting_area(self.img)
        else:
            return StableDiffusionCommand._determine_active_area(self)

