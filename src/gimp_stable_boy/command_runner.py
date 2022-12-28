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

from time import time, sleep
import gtk  # type: ignore
from urlparse import urljoin
from urllib2 import Request, urlopen
from threading import Thread
from collections import namedtuple

from gimpfu import *
from gimp_funcs import pref_value, create_layers, open_images, save_prefs, decode_png
import config
from config import PREFERENCES_SHELF_GROUP as PREFS, DEFAULT_API_URL
import json


class COMMANDSTATUS:
    INITIALIZED = 0
    RUNNING = 1
    DONE = 2
    ERROR  = 3


class PluginCommand(Thread):
    LayerResult = namedtuple('LayerResult', 'name img children')
    CommandMetadata = namedtuple('CommandMetadata', 'proc_name, blurb, help, author, copyright, date, label, imagetypes, params, results')
    metadata = None
    command_runner = None

    @classmethod
    def run_command(cls, *args, **kwargs):
        kwargs.update(dict(zip((param[1] for param in cls.metadata.params), args))) # type: ignore
        save_prefs(cls.metadata.proc_name, **kwargs) # type: ignore
        cls.command_runner(cls(**kwargs))  # type: ignore <== command_runner runs an instance of command class

    def __init__(self, **kwargs):
        Thread.__init__(self)
        self.status = COMMANDSTATUS.INITIALIZED


def run_command(cmd):
    cmd.start()
    cmd.join()
    gimp.progress_update(100)

def run_sd_command(cmd):
    try:
        gimp.progress_init('Processing ...')
        request_start_time = time()
        cmd.start()
        while cmd.status == 'RUNNING':
            sleep(1)
            time_spent = time() - request_start_time
            if config.TIMEOUT_REQUESTS:
                gimp.progress_update(time_spent / float(cmd.timeout))
                if time_spent > cmd.timeout and config.TIMEOUT_REQUESTS:
                    raise Exception('Timed out waiting for response')
        gimp.progress_update(100)
        print(cmd.status)
        if cmd.status == COMMANDSTATUS.DONE:
            cmd.join()
            cmd.img.undo_group_start()
            apply_inpainting_mask = hasattr(cmd, 'apply_inpainting_mask') and cmd.apply_inpainting_mask
            create_layers(cmd.img, cmd.layers, cmd.x, cmd.y, apply_inpainting_mask)
            open_images(cmd.images)
            cmd.img.undo_group_end()
        elif cmd.status == COMMANDSTATUS.ERROR:
            raise Exception(cmd.error_msg)
    except Exception as e:
        error_dialog = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, str(e))
        error_dialog.run()
