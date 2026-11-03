import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.request
import urllib.error
from http.server import ThreadingHTTPServer

sys.path.insert(0,str(Path(__file__).parents[1]/'app'))
from local_setup import LocalSetup, handler_for, validate_settings
from companion import SafetyError
from linux_adapter import own_append, title_key
from astrbot_backend import session_id


class FakeAdapter:
    def __init__(self,path):self.profile=path;self.avatar='a'*64;self.chat='Class group';self.chat_avatar='c'*64
    def status(self):return {'ok':True}
    def observe(self):return {'chat':self.chat,'title':self.chat+' (12)','avatar_sha256':self.avatar,
        'window_id':10,'pid':123,'size':[1280,900],'chat_avatar_sha256':self.chat_avatar,'account_preview':'data:image/png;base64,preview'}
    def bind(self,seen,label,kind,ns):
        value={**seen,'kind':kind,'account_label':label,'namespace':ns}
        self.profile.write_text(json.dumps(value));return value
    def snapshot(self,chat):return {'ok':True,'chat':chat,'verified_chat':True,'messages':[]}


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)
        self.env=patch.dict(os.environ,{'BAGUETTE_RUNTIME':self.tmp.name})
        self.env.start();self.adapter=FakeAdapter(self.path/'linux-binding.json');self.setup=LocalSetup(self.adapter)
    def tearDown(self):
        self.setup.app.store.db.close();self.env.stop();self.tmp.cleanup()
    def bind(self,kind='group',label='Chosen account'):
        obs=self.setup.observe()
        return self.setup.bind({'observation_id':obs['observation_id'],'account_label':label,'kind':kind,'confirm':True})

    def test_first_run_is_paused_and_has_no_chat_or_key(self):
        s=self.setup.status();self.assertFalse(s['status']['enabled']);self.assertFalse(s['setup']['api_key_configured'])
        self.assertEqual(s['setup']['selected_chat'],[])

    def test_api_key_is_private_and_never_returned(self):
        secret='fake-test-key-value'
        result=self.setup.save({'api_key':secret,'bot_id':'Fish','proxy':'direct'})
        self.assertNotIn(secret,json.dumps(result));self.assertNotIn(secret,(self.path/'installation.json').read_text())
        self.assertEqual((self.path/'credentials.env').stat().st_mode&0o777,0o600)
        self.setup.save({'api_key':'','bot_id':'Fish'})
        self.assertIn(secret,(self.path/'credentials.env').read_text())

    def test_key_newline_injection_is_rejected(self):
        with self.assertRaises(SafetyError):validate_settings({'api_key':'key\nOTHER=value'})
        self.assertFalse((self.path/'credentials.env').exists())

    def test_key_cannot_choose_arbitrary_proxy_provider(self):
        with self.assertRaises(SafetyError):validate_settings({'proxy':'https://elsewhere/path'})
        with self.assertRaises(SafetyError):validate_settings({'deepseek_model':'other-provider'})

    def test_chosen_account_and_one_group_are_bound_without_small_account_requirement(self):
        result=self.bind(label='My existing account')
        self.assertEqual(result['setup']['account_label'],'My existing account')
        self.assertEqual(self.setup.app.settings.selected_chats,['Class group'])
        self.assertTrue(self.setup.app.spare_verified)
        self.assertFalse(self.setup.app.enabled)

    def test_other_account_has_separate_consumed_inputs_and_memory(self):
        self.bind();first=session_id('Class group')
        self.setup.app.store.remember('Class group',[{'sender':'OTHER','text':'private first account memory'}])
        self.adapter.avatar='b'*64;self.bind(label='Second account')
        self.assertNotEqual(first,session_id('Class group'))
        self.assertEqual(self.setup.app.store.history('Class group',10),[])

    def test_same_account_can_reselect_chat_without_losing_its_account_scope(self):
        self.bind();first=session_id('Class group')
        self.adapter.chat='Another group';self.bind()
        self.adapter.chat='Class group';self.bind()
        self.assertEqual(first,session_id('Class group'))

    def test_designated_private_chat_is_not_an_owner_login(self):
        self.bind(kind='private',label='Normal account')
        from baguette_config import load_config
        self.assertEqual(load_config()['private_chats'],['Class group'])
        self.assertEqual(self.setup.app.model.group_chats,set())
        self.assertNotEqual(load_config()['owner_id'],load_config()['account_label'])

    def test_same_named_different_chat_has_separate_local_history(self):
        self.bind();self.setup.app.store.remember('Class group',[{'sender':'OTHER','text':'Only first group'}])
        from baguette_config import load_config
        first=load_config()['conversation_namespace']
        self.adapter.chat_avatar='d'*64;self.bind()
        self.assertNotEqual(first,load_config()['conversation_namespace'])
        self.assertEqual(self.setup.app.store.history('Class group',10),[])

    def test_preview_must_be_explicitly_confirmed(self):
        obs=self.setup.observe()
        with self.assertRaises(SafetyError):self.setup.bind({'observation_id':obs['observation_id'],'account_label':'A','kind':'group','confirm':False})
        self.assertFalse(self.adapter.profile.exists())

    def test_expired_preview_cannot_bind(self):
        obs=self.setup.observe();issued_at=self.setup.observation[1]
        # A freshly booted runner may have a monotonic clock below 180 seconds.
        # Advance from the actual preview time rather than assuming zero is old.
        with patch('local_setup.time.monotonic',return_value=issued_at+181):
            with self.assertRaises(SafetyError):self.setup.bind({'observation_id':obs['observation_id'],'account_label':'A','kind':'group','confirm':True})
        self.assertFalse(self.adapter.profile.exists())

    def test_uncertain_send_blocks_account_switch_and_start(self):
        self.bind();self.setup.app.store.delivery('Class group','uncertain','possible outgoing')
        self.adapter.avatar='b'*64
        with self.assertRaises(SafetyError):self.setup.observe()
        with self.assertRaises(SafetyError):self.setup.start()

    def test_active_setup_cannot_be_changed(self):
        self.bind();self.setup.job['state']='ready'
        auth=self.path/'brain/auth.json';auth.parent.mkdir();auth.write_text('{}')
        self.setup.start()
        with self.assertRaises(SafetyError):self.setup.save({'bot_id':'Another'})
        with self.assertRaises(SafetyError):self.setup.observe()
        self.setup.app.pause()

    def test_browser_origin_cannot_save_api_key(self):
        server=ThreadingHTTPServer(('127.0.0.1',0),handler_for(self.setup))
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            url=f'http://127.0.0.1:{server.server_port}/api/setup/save'
            req=urllib.request.Request(url,data=b'{"api_key":"fake"}',headers={'Content-Type':'application/json','Origin':'https://foreign.invalid'})
            op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with self.assertRaises(urllib.error.HTTPError) as error:op.open(req)
            self.assertEqual(error.exception.code,403);self.assertFalse(self.setup.credentials.exists())
            with op.open(url.replace('/save','')) as r:data=json.load(r)
            self.assertFalse(data['setup']['api_key_configured'])
        finally:server.shutdown();server.server_close();thread.join()


class LinuxVerificationTests(unittest.TestCase):
    def test_own_reply_can_be_confirmed_despite_new_group_traffic(self):
        a=[{'sender':'OTHER','text':'old incoming'},{'sender':'ME','text':'first reply'}]
        b=[{'sender':'ME','text':'first reply'},{'sender':'OTHER','text':'new incoming'}, {'sender':'ME','text':'new reply'}]
        self.assertTrue(own_append(a,b,'new reply'))
    def test_already_visible_matching_text_is_not_a_new_send(self):
        a=[{'sender':'ME','text':'same'}]
        self.assertFalse(own_append(a,a,'same'))
    def test_outgoing_must_be_mine_and_exact(self):
        self.assertFalse(own_append([], [{'sender':'OTHER','text':'reply'}],'reply'))
        self.assertFalse(own_append([], [{'sender':'ME','text':'other'}],'reply'))
    def test_group_name_only_strips_member_count(self):
        self.assertEqual(title_key('Grade 11 (120)'),'Grade 11')
        self.assertEqual(title_key('Name (other)'),'Name (other)')


if __name__=='__main__':unittest.main()
