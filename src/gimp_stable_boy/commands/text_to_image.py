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
from _command import StableDiffusionCommand


class Txt2ImgCommand(StableDiffusionCommand):
    uri = 'sdapi/v1/txt2img'
    metadata = StableDiffusionCommand.CommandMetadata(
        sb.__prefix__ + "-txt2img",
        sb.__name__ + sb.__version__ + " - Text to Image",
        sb.__description__,
        sb.__author__,
        sb.__author__,
        sb.__year__,
        sb.__menu__ + "/Text to Image",
        "*",
        [
            (gimpfu.PF_STRING, 'prompt', 'Prompt', ''),
            (gimpfu.PF_STRING, 'negative_prompt', 'Negative prompt', ''),
            (gimpfu.PF_STRING, 'seed', 'Seed', '-1'),
            (gimpfu.PF_SLIDER, 'steps', 'Steps', 25, (1, 150, 25)),
            (gimpfu.PF_OPTION, 'sampler_index', 'Sampler', 0, sb.config.SAMPLERS),
            (gimpfu.PF_BOOL,   'restore_faces', 'Restore faces', False),
            (gimpfu.PF_SLIDER, 'cfg_scale', 'CFG', 7.5, (0, 20, 0.5)),
            (gimpfu.PF_SLIDER, 'num_images', 'Number of images', 1, (1, 4, 1)),
            (gimpfu.PF_OPTION, 'img_target', 'Results as', 0, sb.config.IMAGE_TARGETS),
        ],
        [],)
