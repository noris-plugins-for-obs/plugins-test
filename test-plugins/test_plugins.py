'''
Test all plugins are loaded
'''

import unittest
from onsdriver import obstest

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
                'asynchronous-audio-source',
                'loudness-dock',
                'audio-video-sync-dock',
                'vnc',
        ]

        for exp in modules_exp:
            with self.subTest(name=exp):
                self.assertIn(exp, modules_wo_obs)


if __name__ == '__main__':
    unittest.main()
