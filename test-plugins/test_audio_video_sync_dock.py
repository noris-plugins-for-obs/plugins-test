'''
Test Audio Video Sync Dock
'''

import json
import os.path
import time
import unittest
import urllib.request
from onsdriver import obstest, obsui


def _download_cache_url(url):
    base = os.path.basename(url)
    cache = os.path.abspath(base)
    if os.path.exists(cache):
        return cache

    print(f'Info: Downloading {url}')
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as res:
        with open(cache, 'wb') as fw:
            while True:
                data = res.read(8192)
                if not data:
                    break
                fw.write(data)

    return cache


class AudioVideoSyncDockTest(obstest.OBSTest):
    'Major tests'

    def setUp(self, config_name='saved-config', run=False):
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
                {"text": "Audio Video Sync", "checked": False}
            ]
        })

    def _dock_start(self):
        ui = obsui.OBSUI(self.obs.get_obsws())
        ui.request('widget-invoke', {
            'path': [
                {"className": "OBSDock"},
                {"className": "SyncTestDock"},
                {"className": "QPushButton", "text": "Start"},
                ],
                'method': 'click',
        })

    def _dock_stop(self):
        ui = obsui.OBSUI(self.obs.get_obsws())
        ui.request('widget-invoke', {
            'path': [
                {"className": "OBSDock"},
                {"className": "SyncTestDock"},
                {"className": "QPushButton", "text": "Stop"},
                ],
                'method': 'click',
        })

    def _get_latency_text(self, object_name='latencyDisplay'):
        cl = self.obs.get_obsws()
        ui = obsui.OBSUI(cl)

        w = ui.widget_list(path=[
            {"className": "OBSDock"},
            {"className": "SyncTestDock"},
            {"className": "QLabel", "objectName": object_name},
        ])
        return w['text']

    def _create_image_input(self, scene, name, filename):
        cl = self.obs.get_obsws()
        cl.send('CreateInput', {
            'inputName': name,
            'sceneName': scene,
            'inputKind': 'image_source',
            'inputSettings': {
                'file': filename,
            },
        })

    def _create_media_input(self, scene, name, filename):
        cl = self.obs.get_obsws()
        cl.send('CreateInput', {
            'inputName': name,
            'sceneName': scene,
            'inputKind': 'ffmpeg_source',
            'inputSettings': {
                'local_file': filename,
            },
        })

    def _create_sync_pattern_media(self, scene, name):
        filename = _download_cache_url(
                'https://norihiro.github.io/obs-audio-video-sync-dock/sync-pattern-3000-small.mp4'
        )
        self._create_media_input(scene=scene, name=name, filename=filename)

    def test_dock(self):
        self.obs.run()
        self._create_sync_pattern_media(scene='Scene', name='media')

        self._show_dock()
        time.sleep(1)

        self.assertEqual(self._get_latency_text(), '-')
        self.assertEqual(self._get_latency_text('latencyPolarity'), '-')
        self.assertEqual(self._get_latency_text('indexDisplay'), '-')
        self.assertEqual(self._get_latency_text('frequencyDisplay'), '-')
        self.assertEqual(self._get_latency_text('videoIndexDisplay'), '-')
        self.assertEqual(self._get_latency_text('audioIndexDisplay'), '-')

        self._dock_start()
        time.sleep(3)

        self.assertRegex(self._get_latency_text(), r'^-?[0-9.]* ms$')
        self.assertRegex(self._get_latency_text('latencyPolarity'), r'^Audio (early|lagged)$')
        self.assertRegex(self._get_latency_text('indexDisplay'), r'^[0-9]+$')
        self.assertRegex(self._get_latency_text('frequencyDisplay'), r'^[1-9][0-9]* Hz$')
        self.assertRegex(self._get_latency_text('videoIndexDisplay'), r'^[0-9]+ \([0-9]+% missed\)')
        self.assertRegex(self._get_latency_text('audioIndexDisplay'), r'^[0-9]+ \([0-9]+% missed\)')

        self._dock_stop()
        time.sleep(1)

    @unittest.skip('complicated')
    def test_monitor(self):
        cfg = self.obs.config.get_global_cfg('AudioVideoSyncDock')
        cfg['ListMonitor'] = 'true'
        self.obs.config.save_global_cfg()
        self.obs.run()
        cl = self.obs.get_obsws()
        self._create_sync_pattern_media(scene='Scene', name='media')
        cl.send('CreateInput', {
            'inputName': 'monitor',
            'sceneName': 'Scene',
            'inputKind': 'net.nagater.obs-audio-video-sync-dock.monitor',
            'inputSettings': {
            },
        })

        self._show_dock()
        self._dock_start()
        time.sleep(3)
        self._dock_stop()
        time.sleep(1)
        self._dock_start()
        time.sleep(1)
        self._dock_stop()

    @unittest.skip('complicated')
    def test_monitor1(self):
        cfg = self.obs.config.get_global_cfg('AudioVideoSyncDock')
        cfg['ListMonitor'] = 'true'
        self.obs.config.save_global_cfg()
        self.obs.run()
        cl = self.obs.get_obsws()
        self._create_sync_pattern_media(scene='Scene', name='media')

        self._show_dock()
        self._dock_start()
        time.sleep(1)
        cl.send('CreateInput', {
            'inputName': 'monitor',
            'sceneName': 'Scene',
            'inputKind': 'net.nagater.obs-audio-video-sync-dock.monitor',
            'inputSettings': {
            },
        })
        time.sleep(2)
        cl.send('RemoveInput', {
            'inputName': 'monitor',
        })
        time.sleep(1)
        self._dock_stop()

    @unittest.skip('complicated')
    def test_lag_and_early(self):
        self.obs.run()
        cl = self.obs.get_obsws()
        self._create_sync_pattern_media(scene='Scene', name='media')

        self._show_dock()
        time.sleep(1)

        self._dock_start()

        first = True
        for latency in (-100, -400, +150, +400, -150):
            with self.subTest(latency=latency):
                cl.send('SetInputAudioSyncOffset', {
                    'inputName': 'media',
                    'inputAudioSyncOffset': latency,
                })
                time.sleep(2)
                text = self._get_latency_text()
                polarity = self._get_latency_text('latencyPolarity')
                print(f'Measured {text} ({polarity}) expected {latency} ms')
                if not first:
                    self.assertAlmostEqual(float(text.split()[0]), latency, delta=100)
                    if latency < -100:
                        self.assertEqual(polarity, 'Audio early')
                    elif latency > 100:
                        self.assertEqual(polarity, 'Audio lagged')
            first = False

    @unittest.skip('complicated')
    def test_p010(self):
        profile = self.obs.config.get_profile()
        profile['Video']['ColorFormat'] = 'P010'
        profile['Video']['ColorSpace'] = '2100PQ'
        profile.save()

        self.obs.run()
        self._create_sync_pattern_media(scene='Scene', name='media')

        self._show_dock()
        self._dock_start()
        time.sleep(3)

        self.assertRegex(self._get_latency_text(), r'^-?[0-9.]* ms$')
        self.assertRegex(self._get_latency_text('latencyPolarity'), r'^Audio (early|lagged)$')
        self.assertRegex(self._get_latency_text('indexDisplay'), r'^[0-9]+$')
        self.assertRegex(self._get_latency_text('frequencyDisplay'), r'^[1-9][0-9]* Hz$')
        self.assertRegex(self._get_latency_text('videoIndexDisplay'), r'^[0-9]+ \([0-9]+% missed\)')
        self.assertRegex(self._get_latency_text('audioIndexDisplay'), r'^[0-9]+ \([0-9]+% missed\)')

    @unittest.skip('complicated')
    def test_video_formats(self):
        testcases = (
                { 'ColorFormat': 'I010', },
                { 'ColorFormat': 'P216', },
                { 'ColorFormat': 'P416', },
                { 'ColorFormat': 'RGB', },
        )
        first = True
        for testcase in testcases:
            with self.subTest(**testcase):
                if not first:
                    self.setUp()
                first = False
                profile = self.obs.config.get_profile()
                for k, v in testcase.items():
                    profile['Video'][k] = v
                profile.save()
                self._test_sync()
                self.obs.shutdown()
                self.assertEqual(self.memory_leak(), 0)

    def _test_sync(self):
        self.obs.run()
        self._create_sync_pattern_media(scene='Scene', name='media')

        self._show_dock()
        self._dock_start()
        for _ in range(6):
            time.sleep(0.5)
            if self._get_latency_text() != '-':
                break

        self.assertRegex(self._get_latency_text(), r'^-?[0-9.]* ms$')
        self.assertRegex(self._get_latency_text('latencyPolarity'), r'^Audio (early|lagged)$')
        self.assertRegex(self._get_latency_text('indexDisplay'), r'^[0-9]+$')
        self.assertRegex(self._get_latency_text('frequencyDisplay'), r'^[1-9][0-9]* Hz$')
        self.assertRegex(self._get_latency_text('videoIndexDisplay'), r'^[0-9]+ \([0-9]+% missed\)')
        self.assertRegex(self._get_latency_text('audioIndexDisplay'), r'^[0-9]+ \([0-9]+% missed\)')

    def test_blank(self):
        self.obs.run()

        self._show_dock()
        self._dock_start()
        time.sleep(3)

        self.assertEqual(self._get_latency_text(), '-')
        self.assertEqual(self._get_latency_text('latencyPolarity'), '-')
        self.assertEqual(self._get_latency_text('indexDisplay'), '-')
        self.assertEqual(self._get_latency_text('frequencyDisplay'), '-')
        self.assertEqual(self._get_latency_text('videoIndexDisplay'), '-')
        self.assertEqual(self._get_latency_text('audioIndexDisplay'), '-')

    @unittest.skip('complicated')
    def test_broken_qr(self):
        import qrcode # pylint: disable=import-outside-toplevel
        img = qrcode.make('A=B,C=')
        img_name = './test_broken_qr.jpeg'
        img.save(img_name)
        self.obs.run()
        self._create_image_input(scene='Scene', name='media', filename=os.path.abspath(img_name))

        self._show_dock()
        self._dock_start()
        time.sleep(3)

        self.assertEqual(self._get_latency_text(), '-')
        self.assertEqual(self._get_latency_text('latencyPolarity'), '-')
        self.assertEqual(self._get_latency_text('indexDisplay'), '-')
        self.assertEqual(self._get_latency_text('frequencyDisplay'), '-')
        self.assertEqual(self._get_latency_text('videoIndexDisplay'), '-')
        self.assertEqual(self._get_latency_text('audioIndexDisplay'), '-')

    @unittest.skip('complicated')
    def test_flip(self):
        self.obs.run()
        cl = self.obs.get_obsws()
        self._create_sync_pattern_media(scene='Scene', name='media')
        item = cl.send('GetSceneItemId', {'sceneName': 'Scene', 'sourceName': 'media'})
        print(cl.send('SetSceneItemTransform', {
            'sceneName': 'Scene',
            'sceneItemId': item.scene_item_id,
            'sceneItemTransform': {
                'scaleX': -1.0,
                'positionX': 1280.0,
            }
        }))

        self._show_dock()
        self._dock_start()
        for _ in range(6):
            time.sleep(0.5)
            if self._get_latency_text() != '-':
                break

        self.assertRegex(self._get_latency_text(), r'^-?[0-9.]* ms$')
        self.assertRegex(self._get_latency_text('latencyPolarity'), r'^Audio (early|lagged)$')
        self.assertRegex(self._get_latency_text('indexDisplay'), r'^[0-9]+$')
        self.assertRegex(self._get_latency_text('frequencyDisplay'), r'^[1-9][0-9]* Hz$')
        self.assertRegex(self._get_latency_text('videoIndexDisplay'), r'^[0-9]+ \([0-9]+% missed\)')
        self.assertRegex(self._get_latency_text('audioIndexDisplay'), r'^[0-9]+ \([0-9]+% missed\)')



if __name__ == '__main__':
    unittest.main()
