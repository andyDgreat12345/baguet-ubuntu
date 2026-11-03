"""Local bilingual setup and runner for the Ubuntu desktop container."""
from __future__ import annotations

import json
import mimetypes
import os
from pathlib import Path
import secrets
import subprocess
import sys
import threading
import time
import urllib.request
from http.server import ThreadingHTTPServer
from urllib.parse import urlsplit

from baguette_config import BASE, DEFAULTS, load_config, runtime_path
from companion import Companion, CompanionError, Store, Settings, SafetyError, make_handler, restore_run_intent
from astrbot_backend import AstrBotModel
from linux_adapter import LinuxWeChatAdapter


def write_private(path,value):
    path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');tmp.chmod(0o600);tmp.replace(path)


def validate_settings(body):
    allowed={'api_key','bot_id','deepseek_model','persona_note','group_participation','proxy'}
    if set(body)-allowed:raise SafetyError('Unknown setup field / 未知设置项')
    result={}
    for name in allowed-{'api_key'}:
        if name not in body:continue
        value=body[name]
        if not isinstance(value,str) or any(ord(c)<32 and c not in '\n\t' for c in value):raise SafetyError('Invalid '+name)
        if len(value)>(4000 if name=='persona_note' else 200):raise SafetyError('Setting too long: '+name)
        result[name]=value.strip()
    if 'bot_id' in result and (not result['bot_id'] or '\n' in result['bot_id']):raise SafetyError('Enter the bot name used in mentions / 请填写被@时使用的名字')
    if result.get('group_participation','directed') not in {'directed','active'}:raise SafetyError('Invalid response policy')
    if 'deepseek_model' in result and result['deepseek_model'] not in {'deepseek-flash','deepseek-chat','deepseek-reasoner'}:raise SafetyError('Select a supported DeepSeek model')
    proxy=result.get('proxy','direct')
    if proxy!='direct':
        u=urlsplit(proxy)
        if u.scheme!='http' or not u.hostname or not u.port or u.username or u.password:raise SafetyError('Proxy must be direct or an HTTP proxy URL')
    key=body.get('api_key','')
    if not isinstance(key,str) or len(key)>512 or any(c.isspace() for c in key):raise SafetyError('Invalid API key; spaces/newlines are not accepted')
    return result,key


class LocalSetup:
    def __init__(self,adapter=None):
        self.runtime=runtime_path();self.runtime.mkdir(parents=True,exist_ok=True,mode=0o700)
        self.runtime.chmod(0o700);self.adapter=adapter or LinuxWeChatAdapter()
        config=self.runtime/'installation.json'
        if not config.exists():
            value=dict(DEFAULTS);value.update(deployment_mode='linux',group_chats=[],private_chats=[],
                account_namespace=secrets.token_hex(16),vision_model='qwen3.5:2b',
                vision_base_url='http://ollama:11434/v1',embedding_base_url='http://ollama:11434',
                persona_note='大肥鱼是机灵、有点嘴硬但友善的聊天伙伴。通常只回一短句：中文约5–18字，英文约2–7词，随会话自然切换。可以用俚语和轻松吐槽，不机械翻译、不反复自我介绍、不像客服。先理解对象、语气和上下文，再决定接梗、认真回答或保持安静；不编造看不到的图片内容。推理和工具过程留在内部。学习本会话中反复出现的用语和明确纠正，不把机器人自己的回复当成人类偏好。')
            write_private(config,value)
        self.job={'state':'idle','step':'Enter your API key / 填写 API key'}
        self.job_lock=threading.Lock();self.observation=None
        self.stop=threading.Event();self.credentials=self.runtime/'credentials.env'
        self.app=Companion(self.adapter,self.model(),self.store(),Settings(scope='selected_chats',poll_interval=3,
            min_reply_interval=30,max_calls_per_hour=200,max_reply_chars=120,history_limit=64,max_context_chars=80000),
            isolation_ready=True,spare_verified=self.adapter.profile.exists(),settings_path=self.runtime/'settings.json')
        self.app.run_intent_path=self.runtime/'run-intent.json'
        self.app.log('info','Choose one chat; messages elsewhere are outside the selected scope / 请选择一个指定会话')
        self.last_status=self.app.status()

    def store(self):
        cfg=load_config();ns=cfg['account_namespace'];conv=cfg.get('conversation_namespace','unbound')
        for value in [ns,conv]:
            if not isinstance(value,str) or not __import__('re').fullmatch(r'[a-zA-Z0-9_-]{1,64}',value):raise SafetyError('Invalid account/conversation namespace')
        return Store(self.runtime/('messages-'+ns+'-'+conv+'.sqlite3'))

    def model(self):
        cfg=load_config();os.environ['COMPANION_GROUP_PARTICIPATION']=cfg['group_participation']
        os.environ['COMPANION_MENTION_ALIASES_JSON']=json.dumps([cfg['bot_id'],'大肥鱼','肥鱼'])
        m=AstrBotModel(self.runtime/'brain/auth.json');m.group_chats=set(cfg['group_chats']);return m

    def paused(self):
        if self.app.enabled:raise SafetyError('Pause before changing setup / 修改设置前请先暂停')
        if self.app.store.pending_deliveries():raise SafetyError('An uncertain send must be inspected before changing chat/account / 请先核对结果不明的发送')

    def status(self):
        cfg=load_config()
        health=self.app.health()
        if self.app.lock.acquire(blocking=False):
            try:self.last_status=self.app.status()
            finally:self.app.lock.release()
        current={**self.last_status,'enabled':health['enabled'],'last_error':health['last_error'],
                 'state':'error' if health['last_error'] else 'running' if health['enabled'] else 'paused',
                 'responding':health['worker_busy']}
        return {'setup':{'api_key_configured':self.credentials.exists() and bool(self.credentials.read_text().strip()),
            'bot_id':cfg['bot_id'],'deepseek_model':cfg['deepseek_model'],'persona_note':cfg['persona_note'],
            'group_participation':cfg['group_participation'],'proxy':cfg['proxy'],
            'selected_chat':self.app.settings.selected_chats,'account_label':cfg.get('account_label',''),
            'job':dict(self.job),'desktop_url':'/desktop.html',
            'desktop_password':((self.runtime/'desktop-password').read_text().strip()
                                if (self.runtime/'desktop-password').exists() else ''),
            'platform':'Ubuntu 24.04 / Linux X11','stickers':{'recognition':'original QQ pipeline','favorites_sending':False}},
            'status':current}

    def save(self,body):
        with self.app.lock:
            self.paused();values,key=validate_settings(body)
            if self.job_lock.locked():raise SafetyError('Wait for preparation before changing settings / 准备期间请稍后再修改设置')
            cfg=load_config();cfg.update(values);write_private(self.runtime/'installation.json',cfg)
            if key:
                tmp=self.credentials.with_suffix('.tmp');tmp.write_text('DEEPSEEK_API_KEY='+key+'\n');tmp.chmod(0o600);tmp.replace(self.credentials)
            self.app.model=self.model()
            self.job={'state':'idle','step':'Saved; press Prepare to apply / 已保存，请点击准备以应用'}
            return self.status()

    def observe(self):
        with self.app.lock:
            self.paused();value=self.adapter.observe();token=secrets.token_urlsafe(32)
            self.observation=(token,time.monotonic(),value)
            return {**{k:value[k] for k in ['chat','title','account_preview']},'observation_id':token}

    def bind(self,body):
        with self.app.lock:
            self.paused()
            if set(body)!={'observation_id','account_label','kind','confirm'} or body['confirm'] is not True:raise SafetyError('Confirm the account and current chat first')
            if not self.observation or not secrets.compare_digest(str(body['observation_id']),self.observation[0]) or time.monotonic()-self.observation[1]>180:raise SafetyError('Preview expired; refresh WeChat / 预览已过期，请重新读取')
            if body['kind'] not in {'group','private'}:raise SafetyError('Invalid chat type')
            label=body['account_label']
            if not isinstance(label,str) or not label.strip() or len(label)>100 or '\n' in label:raise SafetyError('Enter the visible account name / 请填写当前登录账号的显示名')
            cfg=load_config();seen=self.observation[2];accounts=cfg.get('account_namespaces',{})
            if not isinstance(seen.get('chat'),str) or not 0<len(seen['chat'])<=200:
                raise SafetyError('Chat title is invalid or too long / 会话名称无效')
            ns=accounts.get(seen['avatar_sha256']) or secrets.token_hex(16)
            saved=self.adapter.bind(seen,label.strip(),body['kind'],ns)
            accounts[saved['avatar_sha256']]=ns
            chat=saved['chat']
            import hashlib
            identity=hashlib.sha256((ns+'\0'+body['kind']+'\0'+chat+'\0'+saved['chat_avatar_sha256']).encode()).hexdigest()
            conversations=cfg.get('conversation_namespaces',{});conv=conversations.get(identity) or secrets.token_hex(16)
            conversations[identity]=conv
            cfg.update(account_namespace=ns,account_namespaces=accounts,account_label=label.strip(),
                conversation_namespace=conv,conversation_namespaces=conversations,
                group_chats=[chat] if body['kind']=='group' else [],private_chats=[chat] if body['kind']=='private' else [])
            write_private(self.runtime/'installation.json',cfg)
            self.app.store.db.close();self.app.store=self.store();self.app.call_times.clear()
            self.app.last_reply.clear();self.app._fresh_baselines.clear();self.app.pending_delivery_count=0
            self.app.model=self.model();self.app.spare_verified=True
            self.app.update_settings({'scope':'selected_chats','selected_chats':[chat]})
            self.app.last_error='';self.app._persist_run_intent(False)
            self.observation=None
            return self.status()

    def _run(self,argv):
        with (self.runtime/'prepare.log').open('a') as log:
            subprocess.run(list(map(str,argv)),cwd=BASE,env=os.environ.copy(),stdout=log,stderr=subprocess.STDOUT,check=True,timeout=1800)

    def _prepare(self):
        try:
            self.job={'state':'preparing','step':'Preparing original QQ memory / 准备原版QQ记忆'}
            if not (self.runtime/'brain/instance/data/cmd_config.json').exists():self._run([sys.executable,BASE/'scripts/setup_brain.py'])
            self.job={'state':'preparing','step':'Downloading local memory and vision models / 下载本地记忆与识图模型'}
            cfg=load_config();op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
            for model in [cfg['embedding_model'],cfg['vision_model']]:
                req=urllib.request.Request(cfg['embedding_base_url']+'/api/pull',data=json.dumps({'model':model,'stream':False}).encode(),headers={'Content-Type':'application/json'})
                with op.open(req,timeout=1800) as r:
                    result=json.load(r)
                if result.get('status')!='success':raise RuntimeError('Local model pull did not finish')
            self.job={'state':'preparing','step':'Starting DeepSeek relay and AstrBot / 启动QQ框架'}
            self._run([sys.executable,BASE/'scripts/brain.py','start'])
            self._run([sys.executable,BASE/'scripts/brain.py','sync-provider'])
            self._run([sys.executable,BASE/'scripts/brain.py','install-persona','--update'])
            self.app.model=self.model()
            self.app.check_model()
            self.job={'state':'ready','step':'DeepSeek and original QQ memory ready / DeepSeek和QQ记忆已就绪'}
            try:
                wanted=json.loads(self.app.run_intent_path.read_text()).get('enabled') is True
                if wanted and self.app.settings.selected_chats:
                    self.adapter.snapshot(self.app.settings.selected_chats[0])
                    restore_run_intent(self.app,self.app.run_intent_path)
            except (OSError,ValueError):pass
            except CompanionError as exc:
                self.app.last_error=str(exc)
                self.app.log('info','DeepSeek ready; login/chat binding needs recheck / 模型已就绪，请重新核对微信登录与会话')
        except Exception as e:
            self.job={'state':'error','step':'Preparation failed ('+type(e).__name__+'); inspect runtime prepare.log / 首次准备失败，请检查日志'}
        finally:self.job_lock.release()

    def prepare(self):
        self.paused()
        if not self.credentials.exists():raise SafetyError('Save your API key first / 请先保存 API key')
        if self.job_lock.acquire(blocking=False):
            threading.Thread(target=self._prepare,daemon=True).start()
        return self.status()

    def start(self):
        with self.app.lock:
            if self.job.get('state')!='ready':raise SafetyError('Prepare and verify DeepSeek first / 请先准备并验证DeepSeek')
            if len(self.app.settings.selected_chats)!=1:raise SafetyError('Bind exactly one chat first')
            self.adapter.snapshot(self.app.settings.selected_chats[0])
            return self.app.start()


def handler_for(setup):
    base=make_handler(setup.app,BASE/'app/setup.html')
    class Handler(base):
        def do_GET(self):
            if self.path=='/api/deliveries' and setup.app.worker_busy and not setup.app.pending_delivery_count:
                if not self._trusted_request():return self._json(403,{'error':{'message':'Local access only'}})
                return self._json(200,{'pending':[]})
            if self.path=='/desktop.html' or self.path.startswith('/novnc/'):
                if not self._trusted_request():return self._json(403,{'error':{'message':'Local access only'}})
                root=Path('/usr/share/novnc').resolve()
                path=(BASE/'app/desktop.html') if self.path=='/desktop.html' else (root/self.path[len('/novnc/'):]).resolve()
                if self.path!='/desktop.html' and not path.is_relative_to(root):return self._json(403,{'error':{'message':'Invalid asset path'}})
                if not path.is_file():return self._json(404,{'error':{'message':'Desktop asset missing'}})
                data=path.read_bytes();self.send_response(200)
                self.send_header('Content-Type',mimetypes.guess_type(str(path))[0] or 'application/octet-stream')
                self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
                self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data);return
            if self.path=='/api/setup':
                if not self._trusted_request():return self._json(403,{'error':{'message':'Local access only'}})
                return self._json(200,setup.status())
            return super().do_GET()

        def do_POST(self):
            if self.path=='/api/settings':
                return self._json(400,{'error':{'message':'Change the chosen chat through the binding preview / 请通过会话预览修改指定聊天'}})
            actions={'/api/setup/save':setup.save,'/api/setup/observe':lambda _:setup.observe(),
                '/api/setup/bind':setup.bind,'/api/setup/prepare':lambda _:setup.prepare(),
                '/api/start':lambda _:setup.start()}
            if self.path not in actions:return super().do_POST()
            if not self._trusted_request():return self._json(403,{'error':{'message':'Local access only'}})
            try:
                if self.headers.get_content_type()!='application/json':raise SafetyError('JSON required')
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=16000:raise SafetyError('Invalid request size')
                body=json.loads(self.rfile.read(size))
                if not isinstance(body,dict):raise SafetyError('JSON object required')
                result=actions[self.path](body);return self._json(200,result)
            except Exception as e:
                message=str(e) if isinstance(e,SafetyError) or type(e).__name__=='LinuxAdapterError' else 'Local action failed ('+type(e).__name__+')'
                return self._json(400,{'error':{'message':message[:300]}})
    return Handler


def main():
    import fcntl
    os.umask(0o077)
    r=runtime_path();r.mkdir(parents=True,exist_ok=True)
    lock=(r/'setup.lock').open('a')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:raise SystemExit('Baguet is already running')
    setup=LocalSetup()
    if setup.credentials.exists() and (r/'brain/instance/data/cmd_config.json').exists():
        setup.prepare()
    def worker():
        while not setup.stop.wait(setup.app.settings.poll_interval):
            setup.app.poll_once()
    def recovery():
        while not setup.stop.wait(30):
            health=setup.app.health()
            if (setup.job.get('state')=='ready' and not health['worker_busy']
                    and (not health['enabled'] or health['last_error'])):
                try:setup.app.recover()
                except Exception:pass
    threading.Thread(target=worker,daemon=True).start();threading.Thread(target=recovery,daemon=True).start()
    # Container is published only on host loopback. Untrusted Host/Origin checks
    # remain enforced by the inherited handler, including in the container.
    server=ThreadingHTTPServer(('0.0.0.0' if os.getenv('BAGUETTE_CONTAINER')=='1' else '127.0.0.1',8766),handler_for(setup))
    print('Baguet setup: http://127.0.0.1:8766',flush=True)
    try:server.serve_forever()
    finally:setup.stop.set();server.server_close()


if __name__=='__main__':main()
