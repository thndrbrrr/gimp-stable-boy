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

#import ssl
from glob import glob
import os, sys
from importlib import import_module
import inspect
import gimpfu
import gimp_stable_boy as sb

# Fix relative imports in Windows
path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(1, path)


if __name__ == '__main__':

    def is_cmd(obj):
        return inspect.isclass(obj) \
            and obj.__name__ not in ['PluginCommand', 'StableDiffusionCommand'] \
            and 'PluginCommand' in [cls.__name__ for cls in inspect.getmro(obj)]

    cmd_module_locations = [['gimp_stable_boy', 'commands']]
    if sb.config.ENABLE_SCRIPTS:
        cmd_module_locations.append(['gimp_stable_boy', 'commands', 'scripts'])

    registered_cmds = []
    for cmd_module_loc in cmd_module_locations:
        cmd_module_names = [
            '.'.join(cmd_module_loc)
            + '.' + os.path.splitext(os.path.basename(c))[0]
            for c in glob(
                os.path.join(os.path.dirname(__file__),
                             *(cmd_module_loc + ['*.py'])))
        ]
        for cmd_module_name in cmd_module_names:
            for _, cmd_cls in (inspect.getmembers(import_module(cmd_module_name), is_cmd)):
                if cmd_cls.__name__ not in registered_cmds:
                    print('Registering Stable Boy command ' + cmd_cls.__name__)
                    if 'StableDiffusionCommand' in [cls.__name__ for cls in inspect.getmro(cmd_cls)]:
                        cmd_cls.command_runner = sb.run_sd_command
                    else:
                        cmd_cls.command_runner = sb.run_command
                    gimpfu.register(*cmd_cls.metadata, function=cmd_cls.run_command)
                    registered_cmds.append(cmd_cls.__name__)

    # ssl._create_default_https_context = ssl._create_unverified_context
    gimpfu.main()
