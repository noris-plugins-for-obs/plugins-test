'''
Test Loudness Dock
'''

import json
import time
import math
import types
import unittest
from onsdriver import obstest, obsui
import helpers


class LoudnessTestBasic(obstest.OBSTest):
    'Base class to test loudness-dock'

    def setUp(self, config_name='saved-config', run=True):
        super().setUp(run=False, config_name=config_name)

        # Remove AuxAudioDevice1
        sc_name = self.obs.config.get_scenecollection_file()
        sc_data_modified = False
        with open(sc_name, 'r', encoding='utf-8') as fr:
            sc_data = json.load(fr)
        if 'AuxAudioDevice1' in sc_data:
            del sc_data['AuxAudioDevice1']
            sc_data_modified = True
        if sc_data_modified:
            with open(sc_name, 'w', encoding='utf-8') as fw:
                json.dump(sc_data, fw)

        if run:
            self.obs.run()

    def _show_dock(self):
        cl = self.obs.get_obsws()
        ui = obsui.OBSUI(cl)
        ui.request('menu-trigger', {
            'path': [
                {"text": "&Docks"},
                {"text": "Loudness", "checked": False}
            ]
        })

    def _create_tone_input(self, *, scene, name, gain, freq_left=440, freq_right=440):
        cl = self.obs.get_obsws()
        cl.send('CreateInput', {
            'inputName': name,
            'sceneName': scene,
            'inputKind': 'net.nagater.obs.' + 'asynchronous-audio-source',
            'inputSettings': {
                'rate': 48000,
                'freq-0': freq_left,
                'freq-1': freq_right,
            },
        })
        cl.send('CreateSourceFilter', {
            'sourceName': name,
            'filterName': 'gain',
            'filterKind': 'gain_filter',
            'filterSettings': {
                'db': gain,
            },
        })

    def _set_tone_gain(self, name, gain):
        cl = self.obs.get_obsws()
        cl.send('SetSourceFilterSettings', {
            'sourceName': name,
            'filterName': 'gain',
            'filterSettings': {
                'db': gain,
            },
        })

    def _get_ws_values(self, vendor='loudness-dock', name=None):
        cl = self.obs.get_obsws()
        rd = {}
        if name:
            rd['name'] = name
        res = cl.send('CallVendorRequest', {
            'vendorName': vendor,
            'requestType': 'get_loudness',
            'requestData': rd,
        })
        return types.SimpleNamespace(res.response_data)

    def _get_ui_values(self):
        ui = obsui.OBSUI(self.obs.get_obsws())

        widget = ui.widget_list(path=[
            {"className": "OBSDock"},
            {"className": "LoudnessDock"},
        ])

        data = {}
        key_map = (
                ('r128_momentary', 'momentary'),
                ('r128_short', 'short'),
                ('r128_integrated', 'integrated'),
                ('r128_peak', 'peak'),
        )
        for child in widget['children']:
            for k1, k2 in key_map:
                if child['objectName'] == k1:
                    data[k2] = float(child['text'])
        return types.SimpleNamespace(data)

    def _pause(self, pause=True, name=None, by_button=False):
        cl = self.obs.get_obsws()
        if by_button:
            ui = obsui.OBSUI(cl)
            ui.request('widget-invoke', {
                'path': [
                    {"className": "OBSDock"},
                    {"className": "LoudnessDock"},
                    {"objectName": "pauseButton"},
                    ],
                    'method': 'click',
            })
            return
        d = {'pause': pause}
        if name:
            d['name'] = name
        cl.send('CallVendorRequest', {
            'vendorName': 'obs-loudness-dock',
            'requestType': 'pause',
            'requestData': d
        })

    def _reset(self, name=None):
        cl = self.obs.get_obsws()
        d = {}
        if name:
            d['name'] = name
        cl.send('CallVendorRequest', {
            'vendorName': 'obs-loudness-dock',
            'requestType': 'reset',
            'requestData': d
        })

    def _config_open(self):
        cl = self.obs.get_obsws()
        ui = obsui.OBSUI(cl)
        ui.request('widget-invoke', {
            'path': [
                {"className": "OBSDock"},
                {"className": "LoudnessDock"},
                {"className": "QPushButton", "accessibleName": "Settings"},
            ],
            'method': 'click',
        })

    def _config_close(self, button='OK'):
        cl = self.obs.get_obsws()
        ui = obsui.OBSUI(cl)
        ui.request('widget-invoke', {
            'path': [
                {"className": "OBSDock"},
                {"className": "LoudnessDock"},
                {"className": "ConfigDialog"},
                {"className": "QDialogButtonBox",},
                {"className": "QPushButton", "text": button},
            ],
            'method': 'click',
        })

class LoudnessTest(LoudnessTestBasic):
    'Major tests for loudness-dock'

    def test_show_dock(self):
        'Just show dock'
        cl = self.obs.get_obsws()
        ui = obsui.OBSUI(cl)

        self._show_dock()

        menu = ui.menu_list([
                {"text": "&Docks"},
                {"text": "Loudness"},
        ])
        self.assertTrue(menu['checked'])

    @helpers.severity(helpers.SEVERITY_COVERAGE)
    def test_loudness_dock(self):
        'Test values on the dock'
        cl = self.obs.get_obsws()
        ui = obsui.OBSUI(cl)

        gains = [
                (-20.0, 5.0),
                ( -9.9, 0.1),
                #( -0.9, 0.1),
                ( -9.9, 0.1),
                (-19.0, 4.0),
                (-12.0, 0.05),
                ( -6.0, 0.05),
                ( -3.0, 0.05),
        ]

        name = 'tone'
        self._create_tone_input(scene='Scene', name=name, gain=gains[0][0])

        self._show_dock()

        integrated_energy, integrated_time = 0.0, 0.0
        peak_db = gains[0][0]

        for db, t in gains:
            cl.send('SetSourceFilterSettings', {
                'sourceName': name,
                'filterName': 'gain',
                'filterSettings': {
                    'db': db,
                },
            })
            time.sleep(t)

            e = math.pow(10.0, db / 10.0) * t
            print(f'db={db} t={t} e={e}')
            integrated_energy += math.pow(10.0, db / 10.0) * t
            integrated_time += t
            peak_db = max(peak_db, db)

            integrated_db = math.log10(integrated_energy / integrated_time) * 10.0

            ws_values = self._get_ws_values(vendor='obs-loudness-dock')
            ui_values = self._get_ui_values()
            exp = db - 0.691
            integrated_exp = integrated_db - 0.691

            if t >= 0.3:
                print(f'M: ws={ws_values.momentary} ui={ui_values.momentary} expected={exp}')
                print(f'P: ws={ws_values.peak} ui={ui_values.peak} expected={peak_db}')

                self.assertAlmostEqual(ws_values.momentary, exp, delta=1)
                self.assertAlmostEqual(ui_values.momentary, exp, delta=1)

                self.assertAlmostEqual(ws_values.peak, peak_db, delta=1)
                self.assertAlmostEqual(ui_values.peak, peak_db, delta=1)

            if t >= 3.0:
                print(f'S: ws={ws_values.short} ui={ui_values.short} expected={exp}')
                print(f'I: ws={ws_values.integrated} ui={ui_values.integrated} expected={integrated_exp}')

                self.assertAlmostEqual(ws_values.short, exp, delta=1)
                self.assertAlmostEqual(ui_values.short, exp, delta=1)

                self.assertAlmostEqual(ws_values.integrated, integrated_exp, delta=1)
                self.assertAlmostEqual(ui_values.integrated, integrated_exp, delta=1)

        ui.grab(
                path=[
                    {"className": "OBSDock"},
                    {"className": "LoudnessDock"}
                ],
                filename=f'screenshots/{self.name}-window.png', window=True)

    @helpers.severity(helpers.SEVERITY_COVERAGE)
    def test_tabs(self):
        cl = self.obs.get_obsws()
        ui = obsui.OBSUI(cl)

        self._show_dock()

        self._config_open()

        ui.request('widget-invoke', {
            'path': [
                {"className": "OBSDock"},
                {"className": "LoudnessDock"},
                {"className": "ConfigDialog"},
                {"className": "QPushButton", "objectName": "tabTableAdd"},
            ],
            'method': 'click',
        })

        self._config_close()

        def _assert_tab(index, count):
            tab_widget = ui.widget_list(path=[
                {"className": "OBSDock"},
                {"className": "LoudnessDock"},
                {"className": "QTabBar"},
            ])
            self.assertEqual(tab_widget['currentIndex'], index)
            self.assertEqual(tab_widget['count'], count)

        def _assert_pause_button(paused):
            pause_button = ui.widget_list(path=[
                {"className": "OBSDock"},
                {"className": "LoudnessDock"},
                {"objectName": "pauseButton"},
            ])
            self.assertEqual(pause_button['text'], 'Resume' if paused else 'Pause')
            values = self._get_ws_values()
            self.assertEqual(values.paused, paused)

        def _assert_paused_by_ws(name_paused):
            for name, paused in name_paused.items():
                values = self._get_ws_values(name=name)
                self.assertEqual(values.paused, paused)

        time.sleep(1)
        _assert_tab(index=0, count=2)

        _assert_pause_button(paused=False)
        _assert_paused_by_ws({'A': False, 'B': False})
        self._pause()
        _assert_pause_button(paused=True)
        _assert_paused_by_ws({'A': True, 'B': False})

        self._pause(name='A', pause=False)
        _assert_pause_button(paused=False)
        _assert_paused_by_ws({'A': False, 'B': False})
        self._pause(by_button=True)
        _assert_pause_button(paused=True)
        _assert_paused_by_ws({'A': True, 'B': False})
        self._pause(by_button=True)
        _assert_pause_button(paused=False)
        _assert_paused_by_ws({'A': False, 'B': False})
        self._pause(name='A')
        _assert_pause_button(paused=True)
        _assert_paused_by_ws({'A': True, 'B': False})
        self._pause(by_button=True)
        _assert_pause_button(paused=False)
        _assert_paused_by_ws({'A': False, 'B': False})
        self._pause(by_button=True)
        _assert_pause_button(paused=True)
        _assert_paused_by_ws({'A': True, 'B': False})

        self._pause(name='B')
        _assert_pause_button(paused=True)
        _assert_paused_by_ws({'A': True, 'B': True})
        self._pause(name='B', pause=False)
        _assert_pause_button(paused=True)
        _assert_paused_by_ws({'A': True, 'B': False})

        self._pause(pause=False)
        _assert_pause_button(paused=False)
        _assert_paused_by_ws({'A': False, 'B': False})

        scene = 'Scene'
        self._create_tone_input(scene=scene, name='tone', gain=-14.0)
        time.sleep(3)
        self._pause(name='A')
        self._pause(name='B')
        _assert_paused_by_ws({'A': True, 'B': True})
        time.sleep(1)
        values1 = self._get_ws_values()
        values1a = self._get_ws_values(name='A')
        values1b = self._get_ws_values(name='B')
        self.assertEqual(values1a, values1)
        # TODO: Instead of comparing, test 'paused' fields.

        # Switch tab
        self._pause(name='A', pause=False)
        _assert_pause_button(paused=False)
        _assert_paused_by_ws({'A': False, 'B': True})
        ui.request('widget-invoke', {
            'path': [
                {"className": "OBSDock"},
                {"className": "LoudnessDock"},
                {"className": "QTabBar"},
            ],
            'method': 'setCurrentIndex',
            'arg1': 1,
        })
        time.sleep(1)
        values2 = self._get_ws_values()
        self.assertEqual(values1b, values2)
        _assert_pause_button(paused=True)
        self._pause(by_button=True)
        _assert_pause_button(paused=False)
        _assert_paused_by_ws({'A': False, 'B': False})
        self._pause(by_button=True)
        _assert_pause_button(paused=True)
        _assert_paused_by_ws({'A': False, 'B': True})

    @helpers.severity(helpers.SEVERITY_COVERAGE)
    def test_tabs_add_delete(self):
        cl = self.obs.get_obsws()
        ui = obsui.OBSUI(cl)

        self._show_dock()

        def _assert_tabs(count):
            tab_widget = ui.widget_list(path=[
                {"className": "OBSDock"},
                {"className": "LoudnessDock"},
                {"className": "QTabBar"},
            ])
            self.assertEqual(tab_widget['count'], count)

        _assert_tabs(1)

        self._config_open()

        ui.request('widget-invoke', {
            'path': [
                {"className": "OBSDock"},
                {"className": "LoudnessDock"},
                {"className": "ConfigDialog"},
                {"className": "QPushButton", "objectName": "tabTableAdd"},
            ],
            'method': 'click',
        })
        _assert_tabs(2)

        ui.request('widget-invoke', {
            'path': [
                {"className": "OBSDock"},
                {"className": "LoudnessDock"},
                {"className": "ConfigDialog"},
                {"className": "QPushButton", "objectName": "tabTableAdd"},
            ],
            'method': 'click',
        })
        _assert_tabs(3)

        ui.request('widget-invoke', {
            'path': [
                {"className": "OBSDock"},
                {"className": "LoudnessDock"},
                {"className": "ConfigDialog"},
            ],
            'method': 'setTabTableCell',
            'arg1': 0,
            'arg2': 1,
        })

        ui.request('widget-invoke', {
            'path': [
                {"className": "OBSDock"},
                {"className": "LoudnessDock"},
                {"className": "ConfigDialog"},
                {"className": "QPushButton", "objectName": "tabTableDel"},
            ],
            'method': 'click',
        })
        _assert_tabs(2)

        self._config_close()

    @helpers.severity(helpers.SEVERITY_COVERAGE)
    def test_tabs_add_cancel(self):
        cl = self.obs.get_obsws()
        ui = obsui.OBSUI(cl)

        self._show_dock()

        def _assert_tabs(count):
            tab_widget = ui.widget_list(path=[
                {"className": "OBSDock"},
                {"className": "LoudnessDock"},
                {"className": "QTabBar"},
            ])
            self.assertEqual(tab_widget['count'], count)

        _assert_tabs(1)

        self._config_open()

        ui.request('widget-invoke', {
            'path': [
                {"className": "OBSDock"},
                {"className": "LoudnessDock"},
                {"className": "ConfigDialog"},
                {"className": "QPushButton", "objectName": "tabTableAdd"},
            ],
            'method': 'click',
        })
        _assert_tabs(2)

        self._config_close("Cancel")
        _assert_tabs(1)

    @helpers.severity(helpers.SEVERITY_COVERAGE)
    def test_colors_add_delete(self):
        cl = self.obs.get_obsws()
        ui = obsui.OBSUI(cl)

        self._show_dock()

        def _assert_colors(count):
            w = ui.widget_list(path=[
                {"className": "OBSDock"},
                {"className": "LoudnessDock"},
                {"className": "ConfigDialog"},
                {"className": "QTableWidget", "objectName": "colorTable"},
            ])
            self.assertEqual(w['rowCount'], count)

        self._config_open()

        _assert_colors(3)

        ui.request('widget-invoke', {
            'path': [
                {"className": "OBSDock"},
                {"className": "LoudnessDock"},
                {"className": "ConfigDialog"},
                {"className": "QPushButton", "objectName": "colorTableAdd"},
            ],
            'method': 'click',
        })
        _assert_colors(4)

        ui.request('widget-invoke', {
            'path': [
                {"className": "OBSDock"},
                {"className": "LoudnessDock"},
                {"className": "ConfigDialog"},
            ],
            'method': 'setColorTableCell',
            'arg1': 0,
            'arg2': 1,
        })

        ui.request('widget-invoke', {
            'path': [
                {"className": "OBSDock"},
                {"className": "LoudnessDock"},
                {"className": "ConfigDialog"},
                {"className": "QPushButton", "objectName": "colorTableDel"},
            ],
            'method': 'click',
        })
        _assert_colors(3)

        self._config_close()

    @helpers.severity(helpers.SEVERITY_COVERAGE)
    def test_with_pause(self):
        'Test values with pause and resume'
        cl = self.obs.get_obsws()

        gains = [
                (-10.0, 4.0),
                (-16.0, 4.0),
        ]

        scene = 'Scene'
        name = 'tone'
        self._create_tone_input(scene=scene, name=name, gain=gains[0][0])

        self._show_dock()

        for db, t in gains:
            cl.send('SetSourceFilterSettings', {
                'sourceName': name,
                'filterName': 'gain',
                'filterSettings': {
                    'db': db,
                },
            })
            time.sleep(0.5)
            self._reset()
            self._pause(pause=False)
            time.sleep(t)
            self._pause(pause=True)

            ws_values = self._get_ws_values()
            ui_values = self._get_ui_values()
            exp = db - 0.691

            print(f'momentary: ws={ws_values.momentary} ui={ui_values.momentary} expected={exp}')
            print(f'peak: ws={ws_values.peak} ui={ui_values.peak} expected={db}')
            print(f'short: ws={ws_values.short} ui={ui_values.short} expected={exp}')
            print(f'integrated: ws={ws_values.integrated} ui={ui_values.integrated} expected={exp}')

            self.assertAlmostEqual(ws_values.momentary, exp, delta=1)
            self.assertAlmostEqual(ui_values.momentary, exp, delta=1)

            self.assertAlmostEqual(ws_values.peak, db, delta=4)
            self.assertAlmostEqual(ui_values.peak, db, delta=4)

            self.assertAlmostEqual(ws_values.short, exp, delta=1)
            self.assertAlmostEqual(ui_values.short, exp, delta=1)

            self.assertAlmostEqual(ws_values.integrated, exp, delta=1)
            self.assertAlmostEqual(ui_values.integrated, exp, delta=1)

    @helpers.severity(helpers.SEVERITY_COVERAGE)
    def test_abbrev(self):
        cl = self.obs.get_obsws()
        ui = obsui.OBSUI(cl)

        self._show_dock()

        for abbrev in (False, True):
            abbrev_next = not abbrev
            ui.request('widget-invoke', {
                'path': [
                    {"className": "OBSDock"},
                    {"className": "LoudnessDock"},
                    {"className": "QPushButton", "objectName": "configButton"},
                ],
                'method': 'click',
            })

            ui.request('widget-invoke', {
                'path': [
                    {"className": "OBSDock"},
                    {"className": "LoudnessDock"},
                    {"className": "ConfigDialog"},
                    {"className": "QCheckBox", "text": "Abbreviate labels"},
                ],
                'method': 'click',
            })

            ui.request('widget-invoke', {
                'path': [
                    {"className": "OBSDock"},
                    {"className": "LoudnessDock"},
                    {"className": "ConfigDialog"},
                    {"className": "QDialogButtonBox",},
                    {"className": "QPushButton", "text": "OK"},
                ],
                'method': 'click',
            })

            widget = ui.widget_list(path=[
                {"className": "OBSDock"},
                {"className": "LoudnessDock"},
            ])
            label_texts = [
                    child['text'] for child in widget['children'] if child['className']=='QLabel'
            ]
            print(label_texts)
            self.assertIs('M' in label_texts, abbrev_next)
            self.assertIs('S' in label_texts, abbrev_next)
            self.assertIs('I' in label_texts, abbrev_next)
            self.assertIs('Momentary' in label_texts, not abbrev_next)
            self.assertIs('Short-term' in label_texts, not abbrev_next)
            self.assertIs('Integrated' in label_texts, not abbrev_next)


class LoudnessTestComplicated(LoudnessTestBasic):
    'Complicated tests for loudness-dock, each test can modify config.'

    def setUp(self, config_name='saved-config', run=True):
        super().setUp(run=False, config_name=config_name)

    @helpers.severity(helpers.SEVERITY_COVERAGE)
    def test_triggers(self):
        profile = self.obs.config.get_profile()
        profile['LoudnessDock']['n_tabs'] = '2'
        profile['LoudnessDock']['tab.0.name'] = 'A'
        profile['LoudnessDock']['tab.0.track'] = '0'
        profile['LoudnessDock']['tab.0.trigger'] = '0'
        profile['LoudnessDock']['tab.1.name'] = 'B'
        profile['LoudnessDock']['tab.1.track'] = '0'
        profile['LoudnessDock']['tab.1.trigger'] = '2' # by Recording
        profile['SimpleOutput']['RecQuality'] = 'Small' # to pause recording
        profile.save()
        self.obs.run()

        cl = self.obs.get_obsws()

        self._show_dock()

        def _g2l(*argv):
            e = sum(math.pow(10.0, db / 10.0) for db in argv)
            return math.log10(e / len(argv)) * 10.0 - 0.691

        scene = 'Scene'
        name = 'tone'
        self._create_tone_input(scene=scene, name=name, gain=-23.0)
        time.sleep(3)

        cl.send('StartRecord')
        self._set_tone_gain(name=name, gain=-14.0)
        time.sleep(3)
        values1a = self._get_ws_values(name='A')
        values1b = self._get_ws_values(name='B')
        print(f'{values1a} {values1b}')
        self.assertAlmostEqual(values1a.integrated, _g2l(-23.0, -14.0), delta=0.5)
        self.assertAlmostEqual(values1b.integrated, _g2l(-14.0), delta=0.1)

        cl.send('PauseRecord')
        self._set_tone_gain(name=name, gain=-20.0)
        time.sleep(3)
        values_a = self._get_ws_values(name='A')
        self.assertAlmostEqual(values_a.integrated, _g2l(-23.0, -14.0, -20.0), delta=0.5)

        self._set_tone_gain(name=name, gain=-10.0)
        cl.send('ResumeRecord')
        time.sleep(3)

        # TODO: Try Pause unpause recording
        cl.send('StopRecord')
        self._set_tone_gain(name=name, gain=-23.0)
        time.sleep(3)
        values2a = self._get_ws_values(name='A')
        values2b = self._get_ws_values(name='B')
        print(f'{values2a} {values2b}')
        exp_2a = _g2l(-23.0, -14.0, -20.0, -10.0, -23.0)
        exp_2b = _g2l(-14.0, -10.0)
        self.assertAlmostEqual(values2a.integrated, exp_2a, delta=0.5)
        self.assertAlmostEqual(values2b.integrated, exp_2b, delta=0.1)

    @helpers.severity(helpers.SEVERITY_COVERAGE)
    def test_greycolor(self):
        profile = self.obs.config.get_profile()
        profile['LoudnessDock']['n_colors'] = '2'
        profile['LoudnessDock']['color.fg.0'] = f'{0xAAAAAA}'
        profile['LoudnessDock']['color.bg.0'] = f'{0x555555}'
        profile['LoudnessDock']['threshold.0'] = '-23.0'
        profile['LoudnessDock']['color.fg.1'] = f'{0xFFFFFF}'
        profile['LoudnessDock']['color.bg.1'] = f'{0x7F7F7F}'
        profile.save()
        self.obs.run()

        self._show_dock()

        scene = 'Scene'
        name = 'tone'
        self._create_tone_input(scene=scene, name=name, gain=-14.0)
        time.sleep(3)
        # TODO: Check the color


if __name__ == '__main__':
    unittest.main()
