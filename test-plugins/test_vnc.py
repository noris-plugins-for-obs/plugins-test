'''
Test VNC Source
'''

import time
import unittest
from onsdriver import obstest, obsui


def flatten_widgets(widget):
    'Iterate self and all widgets'
    yield widget
    for w in widget['children']:
        yield from flatten_widgets(w)


class VNCTest(obstest.OBSTest):
    'Class to test vnc plugin'

    def setUp(self, config_name='saved-config', run=True):
        super().setUp(run=run, config_name=config_name)

    @unittest.skip('covered by test_properties')
    def test_empty(self):
        cl = self.obs.get_obsws()

        cl.send('CreateInput', {
            'inputName': 'vnc',
            'sceneName': 'Scene',
            'inputKind': 'obs_vnc_source',
            'inputSettings': {
                'host_name': 'localhost',
            },
        })

        time.sleep(1)

    def test_properties(self):
        cl = self.obs.get_obsws()
        ui = obsui.OBSUI(cl)
        self.obs.waive_error(waiver_re=r'.*ConnectClientToTcpAddr6: connect')

        cl.send('CreateInput', {
            'inputName': 'vnc',
            'sceneName': 'Scene',
            'inputKind': 'obs_vnc_source',
            'inputSettings': {
                'host_name': 'localhost',
            },
        })
        cl.send('OpenInputPropertiesDialog', { 'inputName': 'vnc' })
        time.sleep(1)

        w = ui.widget_list(path=[
            {"className": "OBSBasicProperties"},
            {},
            {},
            {"className": "OBSPropertiesView"},
        ])
        labels = [c['text'] for c in flatten_widgets(w) if c['className']=='QLabel']
        print(labels)
        self.assertIn('Host name', labels)
        self.assertIn('Host port', labels)
        self.assertIn('Password', labels)
        self.assertIn('Preferred encodings', labels)


if __name__ == '__main__':
    unittest.main()
