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

import json
import socket
import hashlib
import tempfile
from urlparse import urljoin
from urllib2 import Request, urlopen
from gimp_stable_boy.command_runner import PluginCommand, COMMANDSTATUS
import gimp_stable_boy as sb
from gimp_stable_boy.config import PREFERENCES_SHELF_GROUP as PREFS
from gimpfu import *



class StableDiffusionCommand(PluginCommand):
    uri = ''

    def __init__(self, **kwargs):
        PluginCommand.__init__(self, **kwargs)
        self.url = urljoin(sb.gimp.pref_value(PREFS, 'api_base_url', sb.config.DEFAULT_API_URL), self.uri)
        self.img = kwargs['image']
        self.images = None
        self.layers = None
        self.x, self.y, self.width, self.height = self._determine_active_area()
        print('x, y, w, h: ' + str(self.x) + ', ' + str(self.y) + ', ' + str(self.width) + ', ' + str(self.height))
        self.img_target = sb.config.IMAGE_TARGETS[kwargs.get('img_target', 0)]  # layers are the default img_target
        self.req_data = self._make_request_data(**kwargs)
        if sb.config.TIMEOUT_REQUESTS:
            self.timeout = self._estimate_timeout(self.req_data)
        else:
            self.timeout = socket._GLOBAL_DEFAULT_TIMEOUT  # type: ignore

    def run(self):
        self.status = COMMANDSTATUS.RUNNING
        try:
            if sb.config.LOG_REQUESTS:
                req_path = tempfile.mktemp(prefix='req_', suffix='.json')
                with open(req_path, 'w') as req_file:
                    print('request: ' + req_path)
                    req_file.write(json.dumps(self.req_data))
            sd_request = Request(url=self.url,
                                 headers={'Content-Type': 'application/json'},
                                 data=json.dumps(self.req_data))
            # print(self.req_data)
            self.sd_resp = urlopen(sd_request, timeout=self.timeout)
            if self.sd_resp:
                self.response = json.loads(self.sd_resp.read())
                if sb.config.LOG_REQUESTS:
                    resp_path = tempfile.mktemp(prefix='resp_', suffix='.json')
                    with open(resp_path, 'w') as resp_file:
                        print('response: ' + resp_path)
                        resp_file.write(json.dumps(self.response))
                self._process_response(self.response)
            self.status = COMMANDSTATUS.DONE
        except Exception as e:
            self.status = COMMANDSTATUS.ERROR
            self.error_msg = str(e)
            print(e)
            raise e

    def _process_response(self, resp):

        def _mk_short_hash(img):
            return hashlib.sha1(img.encode("UTF-8")).hexdigest()[:7]

        all_imgs = resp['images']
        if self.img_target == 'Layers':
            self.layers = [
                StableDiffusionCommand.LayerResult(_mk_short_hash(img), img, None) for img in all_imgs
            ]
        elif self.img_target == 'Images':
            self.images = all_imgs


    def _determine_active_area(self):
        return sb.gimp.active_area(self.img)

    def _make_request_data(self, **kwargs):
        return {
            'prompt': kwargs['prompt'],
            'negative_prompt': kwargs['negative_prompt'],
            'steps': kwargs['steps'],
            'sampler_index': sb.config.SAMPLERS[kwargs['sampler_index']],
            'batch_size': int(kwargs['num_images']),
            'cfg_scale': kwargs['cfg_scale'],
            'seed': kwargs['seed'],
            'restore_faces': kwargs['restore_faces'],
            'width': self.width,
            'height': self.height,
        }

    def _estimate_timeout(self, req_data):
        timeout = int(int(req_data['steps'])
                      * int(req_data['batch_size'])
                      * sb.config.TIMEOUT_FACTOR)
        if req_data['restore_faces']:
            timeout = int(timeout * 1.2 * sb.config.TIMEOUT_FACTOR)
        return timeout
