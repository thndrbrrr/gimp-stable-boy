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
from _command import PluginCommand, StableDiffusionCommand


class UpscaleCommand(StableDiffusionCommand):
    uri = 'sdapi/v1/extra-single-image'
    metadata = PluginCommand.CommandMetadata(
        sb.__prefix__ + "-upscale",
        sb.__name__ + sb.__version__ + " - Upscale",
        sb.__description__,
        sb.__author__,
        sb.__author__,
        sb.__year__,
        sb.__menu__ + "/Upscale",
        "*",
        [
            (gimpfu.PF_SLIDER, 'upscaling_resize', 'Upscaling factor', 2, (1, 4, 1)),
            (gimpfu.PF_OPTION, 'upscaler_1', 'Upscaler 1', 0, sb.config.UPSCALERS),
            (gimpfu.PF_OPTION, 'upscaler_2', 'Upscaler 2', 0, sb.config.UPSCALERS),
            (gimpfu.PF_SLIDER, 'extras_upscaler_2_visibility', 'Upscaler 2 visibility', 0, (0, 1, 0.1))
        ],
        [],)

    def _make_request_data(self, **kwargs):
        return {
            'upscaling_resize': int(kwargs['upscaling_resize']),
            'upscaler_1': sb.config.UPSCALERS[kwargs['upscaler_1']],
            'upscaler_2': sb.config.UPSCALERS[kwargs['upscaler_2']],
            'extras_upscaler_2_visibility': kwargs['extras_upscaler_2_visibility'],
            'image': sb.gimp.encode_img(self.img, self.x, self.y, self.width, self.height),
        }

    def _estimate_timeout(self, req_data):
        return (60 if float(req_data['extras_upscaler_2_visibility']) > 0 else 30) * sb.config.TIMEOUT_FACTOR

    def _process_response(self, resp):
        self.images = [resp['image']]
