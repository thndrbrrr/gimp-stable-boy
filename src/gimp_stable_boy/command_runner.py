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
from gimpfu import *
from .config import Config as config
import gimp_funcs


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
        if cmd.status == 'DONE':
            cmd.join()
            cmd.img.undo_group_start()
            gimp_funcs.create_layers(cmd.img, cmd.layers, cmd.x, cmd.y)
            gimp_funcs.open_images(cmd.images)
            cmd.img.undo_group_end()
        elif cmd.status == 'ERROR':
            raise Exception(cmd.error_msg)
    except Exception as e:
        error_dialog = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, str(e))
        error_dialog.run()