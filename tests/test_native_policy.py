import asyncio
import importlib
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).parents[1]))
sys.path.insert(0,str(Path(__file__).parents[1]/'app'))


class NativePolicyTests(unittest.TestCase):
    def module(self):
        if importlib.util.find_spec('astrbot') is None:
            self.skipTest('Install original AstrBot to run native policy integration tests')
        try:
            with tempfile.TemporaryDirectory() as directory:
                old=os.getcwd()
                try:
                    os.chdir(directory)
                    with patch.dict(os.environ,{'ASTRBOT_ROOT':directory}):
                        return importlib.import_module('plugins.wechat_vm_transport.main')
                finally:os.chdir(old)
        except ModuleNotFoundError as e:
            if e.name=='astrbot':self.skipTest('Install original AstrBot to run native policy integration tests')
            raise

    def test_private_chat_cannot_use_admin_or_memory_write_tools(self):
        module=self.module();event=module.WeChatVMEvent.__new__(module.WeChatVMEvent)
        event.get_group_id=lambda:'';event.get_extra=lambda _:{};event.get_sender_name=lambda:'Ordinary contact'
        from astrbot.core.agent.tool import FunctionTool
        tools=[FunctionTool(name=name,description='Test tool',parameters={'type':'object','properties':{}})
               for name in ['recall_long_term_memory','memorize_long_term_memory','execute_python','select_wechat_sticker']]
        req=SimpleNamespace(system_prompt='',func_tool=module.ToolSet(tools=tools))
        instance=module.WeChatVMTransport.__new__(module.WeChatVMTransport)
        asyncio.run(instance.platform_context(event,req))
        self.assertEqual([t.name for t in req.func_tool.tools],['recall_long_term_memory','select_wechat_sticker'])
        self.assertEqual(len(tools),4,'The global tool list must not be modified')

    def test_native_qq_chat_id_is_separate_for_each_account(self):
        module=self.module()
        with patch.object(module,'load_config',return_value={'account_namespace':'account-a'}):first=module.chat_id('Same named group')
        with patch.object(module,'load_config',return_value={'account_namespace':'account-b'}):second=module.chat_id('Same named group')
        self.assertNotEqual(first,second)

    def test_linux_does_not_offer_uncalibrated_sticker_sending(self):
        module=self.module();event=module.WeChatVMEvent.__new__(module.WeChatVMEvent)
        event.get_group_id=lambda:'group';event.get_extra=lambda _:{};event.get_sender_name=lambda:'Member'
        from astrbot.core.agent.tool import FunctionTool
        tools=[FunctionTool(name=name,description='Test',parameters={'type':'object','properties':{}})
               for name in ['recall_long_term_memory','select_wechat_sticker']]
        req=SimpleNamespace(system_prompt='',func_tool=module.ToolSet(tools=tools))
        instance=module.WeChatVMTransport.__new__(module.WeChatVMTransport)
        with patch.object(module,'load_config',return_value={'deployment_mode':'linux'}):
            asyncio.run(instance.platform_context(event,req))
        self.assertEqual([t.name for t in req.func_tool.tools],['recall_long_term_memory'])
        self.assertIn('不编造已发送',req.system_prompt)

    def test_native_qq_memory_separates_identically_named_groups(self):
        module=self.module()
        cfg={'account_namespace':'account-a','deployment_mode':'linux','group_chats':['Same named group'],'private_chats':[],'conversation_namespace':'first-chat'}
        with patch.object(module,'load_config',return_value=cfg):first=module.chat_id('Same named group')
        cfg={**cfg,'conversation_namespace':'second-chat'}
        with patch.object(module,'load_config',return_value=cfg):second=module.chat_id('Same named group')
        self.assertNotEqual(first,second)

    def test_linux_private_sender_named_owner_is_not_an_admin(self):
        module=self.module()
        message=module.AstrBotMessage();message.message_str='hello';message.session_id='private-test'
        message.type=module.MessageType.FRIEND_MESSAGE;message.message=[module.Plain('hello')]
        message.self_id='bot';message.message_id='unit-message'
        message.sender=module.MessageMember('owner','ordinary contact')
        meta=module.PlatformMetadata(name='wechat_vm',description='test',id='wechat-vm')
        with patch.object(module,'load_config',return_value={'deployment_mode':'linux','owner_id':'owner'}):
            event=module.WeChatVMEvent(message,meta,'test-request')
        self.assertFalse(event.get_extra('_api_key_allow_admin_role'))


if __name__=='__main__':unittest.main()
