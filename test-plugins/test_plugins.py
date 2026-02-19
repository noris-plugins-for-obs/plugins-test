'''
Test all plugins are loaded
'''

import re
import unittest
from onsdriver import obstest
import helpers

def _unversioned(name):
    m = re.match(r'(.*)_v[1-9][0-9]*$', name)
    if m:
        return m[1]
    return name

class PluginsTest(obstest.OBSTest):
    'Class to test plugins'

    def test_plugin_list(self):
        'Check expected plugins are loaded by log'
        log = self.obs.get_logfile()
        modules = []
        with open(log, 'r', encoding='utf-8') as fr:
            in_loaded_modules = False
            for line in fr:
                line = line.split(': ', 1)[1].strip()
                if '----------------' in line:
                    in_loaded_modules = False
                elif line == 'Loaded Modules:':
                    in_loaded_modules = True
                elif in_loaded_modules:
                    name = line.rsplit('.', 1)[0]
                    modules.append(name)

        modules_wo_obs = [(n[4:] if n.startswith('obs-') else n) for n in modules]

        modules_exp = [
                'async-audio-filter',
                'asynchronous-audio-source',
                'audio-video-sync-dock',
                'color-monitor',
                'frame-interleave-filter',
                'h8819-source',
                'loudness-dock',
                'main-view-source',
                'mute-filter',
                'text-pthread',
                'vban',
                'vnc',
        ]

        for exp in modules_exp:
            with self.subTest(name=exp):
                self.assertIn(exp, modules_wo_obs)

        ii = helpers.list_inputs(self.obs.get_obsws())
        ii_unversioned = [_unversioned(x) for x in ii]

        print(ii_unversioned)
        inputs_exp = [
                # asynchronous-audio-source
                'net.nagater.obs.asynchronous-audio-source',
                # color-monitor
                'vectorscope_source',
                'waveform_source',
                'histogram_source',
                'net.nagater.obs-color-monitor.zebra_source',
                'net.nagater.obs-color-monitor.falsecolor_source',
                'net.nagater.obs-color-monitor.focuspeaking_source',
                # h8819-source
                'net.nagater.obs-h8819-source.source',
                # main-view-source
                'net.nagater.obs-main-view-source.source',
                # text-pthread
                'obs_text_pthread_source',
                # vban
                'net.nagater.obs-vban.source',
                # vnc
                'obs_vnc_source',
        ]

        for input_name in inputs_exp:
            with self.subTest(input_name=input_name):
                self.assertIn(input_name, ii_unversioned)


if __name__ == '__main__':
    unittest.main()
