"""Ubuntu visual bridge. The official WeChat client owns login and network traffic.

Uses the pinned WeChat-AI ImageProcessor, RapidOCR and layout reader. No WeChat
database or process memory is opened. All actions stay on the selected X11 window.
"""
from __future__ import annotations

import base64
import collections
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import threading
import time

from baguette_config import runtime_path
from companion import CompanionError


class LinuxAdapterError(CompanionError):
    pass


def title_key(text):
    return re.sub(r'\s*[（(]\s*\d+\s*[)）]\s*$', '', text).strip()


def own_append(before, after, text):
    """Require an exact, newly appended own bubble, independent of other traffic."""
    key=lambda s: re.sub(r'\s+', '', s)
    a=[key(m['text']) for m in before if m['sender']=='ME']
    b=[key(m['text']) for m in after if m['sender']=='ME']
    wanted=key(text)
    if not b or b[-1]!=wanted or b.count(wanted)<=a.count(wanted):return False
    if not a:return b==[wanted]
    overlaps=[n for n in range(1,min(len(a),len(b)-1)+1) if a[-n:]==b[:n]]
    return len(overlaps)==1 and overlaps[0]==len(b)-1 and a.count(a[-1])==1


class LinuxWeChatAdapter:
    def __init__(self):
        self.lock=threading.RLock()
        self.vision=None
        self.ocr=None
        self.wm=None
        self.profile=runtime_path()/'linux-binding.json'
        self.cached=None

    @staticmethod
    def command(*args, data=None, timeout=8, binary=False):
        p=subprocess.run(list(map(str,args)),input=data,capture_output=True,
                         text=not binary,timeout=timeout)
        if p.returncode:raise LinuxAdapterError('Desktop command failed: '+str(args[0]))
        return p.stdout if binary else p.stdout.strip()

    def status(self):
        return {'ok':os.name=='posix' and bool(os.environ.get('DISPLAY')),
                'display_available':bool(os.environ.get('DISPLAY')),
                'mode':'Linux X11 visual control','bound':self.profile.exists()}

    def _models(self):
        if self.vision is not None:return
        from wechat_ai_bot.rpa.image_processor import ImageProcessor
        from wechat_ai_bot.rpa.ocr_processor import OCRProcessor
        from wechat_ai_bot.rpa.xfce_window_manager import XFCEWindowManager
        class LayoutReader(XFCEWindowManager):
            def _save_layout_debug(self,screenshot):
                pass  # Never persist an entire chat screenshot as a layout debug file.
        vision=ImageProcessor();vision.setup()
        ocr=OCRProcessor({'use_remote':False,'min_confidence':.78});ocr.setup()
        wm=LayoutReader(vision,ocr,{'window':{'width':1280,'height':900},
            'layout':{'startup_session':'','min_input_height':90,'max_input_height':250}})
        self.vision,self.ocr,self.wm=vision,ocr,wm

    def _windows(self):
        from Xlib import display, X
        d=display.Display();root=d.screen().root
        p=root.get_full_property(d.intern_atom('_NET_CLIENT_LIST'),X.AnyPropertyType)
        result=[]
        for wid in list(p.value) if p else []:
            try:
                w=d.create_resource_object('window',int(wid));cls=' '.join(w.get_wm_class() or []).lower()
                if not any(s in cls for s in ['wechat','weixin']):continue
                if w.get_attributes().map_state!=X.IsViewable:continue
                pid=w.get_full_property(d.intern_atom('_NET_WM_PID'),X.AnyPropertyType)
                if pid is None:continue
                pid=int(pid.value[0]);exe=Path('/proc')/str(pid)/'exe'
                if Path(os.readlink(exe)).name.lower() not in {'wechat','weixin','wechatlinux'}:continue
                g=w.get_geometry();result.append({'id':int(wid),'pid':pid,'width':g.width,'height':g.height})
            except (OSError,ValueError):continue
        d.close()
        return result

    def frame(self):
        self._models()
        windows=self._windows();main=[w for w in windows if w['width']>=800 and w['height']>=550]
        if len(main)!=1:raise LinuxAdapterError('Log into WeChat and open one chat / 请登录微信并打开一个会话')
        if len(windows)!=1:raise LinuxAdapterError('Close WeChat popups before continuing / 请关闭微信弹窗')
        w=main[0]
        self.command('wmctrl','-i','-r',hex(w['id']),'-b','add,fullscreen')
        self.command('xdotool','windowactivate','--sync',w['id'])
        self.command('xdotool','mousemove','700','20');time.sleep(.12)
        self.wm.size_config.width=1280;self.wm.size_config.height=900
        if not self.wm._init_window_part_size():
            raise LinuxAdapterError('WeChat layout not recognized; use light theme, 100% scaling / 请使用浅色和100%缩放')
        shot=self.vision.take_screenshot([0,0,1280,900])
        if shot is None:raise LinuxAdapterError('Could not capture the WeChat desktop')
        left=self.wm.MSG_TOP_X;top=self.wm.MSG_TOP_Y
        title_crop=shot.crop((left+10,4, min(1120,left+460),top-3))
        lines=self.ocr.process_image(image=title_crop)
        title=' '.join(x['label'] for x in lines).strip()
        if not title:raise LinuxAdapterError('The current chat title is unreadable / 无法读取当前会话名')
        chat=title_key(title)
        side=self.wm.SIDE_BAR_WIDTH
        sidebar=self.ocr.process_image(image=shot.crop((side,top,left,900)))
        def matches(text):
            text=title_key(text)
            if text==chat:return True
            prefix=text.rstrip('.…').strip()
            return text.endswith(('…','...')) and len(prefix)>=6 and chat.startswith(prefix)
        rows=[r for r in sidebar if matches(r['label']) and r['pixel_bbox'][0]>35]
        if len(rows)!=1:raise LinuxAdapterError('The selected chat must be uniquely visible in the sidebar / 请让选定会话在左侧列表中唯一可见')
        yy=int(rows[0]['pixel_bbox'][1])+top
        import numpy as np
        strip=np.asarray(shot.crop((left-7,top,left-3,880)),dtype='int16')
        baseline=np.median(strip.reshape(-1,3),axis=0)
        selected=(abs(strip-baseline).max(axis=2).mean(axis=1)>=8)
        anchor=min(len(selected)-1,max(0,yy+15-top))
        if not selected[anchor]:
            raise LinuxAdapterError('Chat row selection could not be verified / 无法核实左侧会话的选中状态')
        begin=end=anchor
        while begin>0 and selected[begin-1]:begin-=1
        while end+1<len(selected) and selected[end+1]:end+=1
        if not 40<=end-begin+1<=100:raise LinuxAdapterError('Selected row geometry is ambiguous / 选中会话的行位置不明确')
        row_top=top+begin
        chat_avatar=shot.crop((side+12,row_top+10,side+44,row_top+42)).convert('RGB')
        chat_identity=hashlib.sha256(chat_avatar.tobytes()).hexdigest()
        avatar=shot.crop((8,25,min(50,self.wm.SIDE_BAR_WIDTH-5),68)).resize((24,24)).convert('RGB')
        identity=hashlib.sha256(avatar.tobytes()).hexdigest()
        return shot,{'title':title,'chat':chat,'avatar_sha256':identity,'chat_avatar_sha256':chat_identity,
                     'window_id':w['id'],'pid':w['pid'],'size':[1280,900],
                     'body':[left,top,self.wm.MSG_WIDTH,self.wm.MSG_HEIGHT]}

    def observe(self):
        with self.lock:
            shot,meta=self.frame()
            avatar=shot.crop((0,0,self.wm.SIDE_BAR_WIDTH,90));buf=io.BytesIO();avatar.save(buf,format='PNG')
            return {**meta,'account_preview':'data:image/png;base64,'+base64.b64encode(buf.getvalue()).decode()}

    def bind(self, observation, account_label, kind, namespace):
        with self.lock:
            _,current=self.frame()
            if any(current[k]!=observation[k] for k in ['title','avatar_sha256','chat_avatar_sha256','window_id','pid','size']):
                raise LinuxAdapterError('WeChat changed since preview; refresh it / 微信已变化，请重新读取')
            value={**current,'account_label':account_label,'kind':kind,'namespace':namespace}
            tmp=self.profile.with_suffix('.tmp');tmp.write_text(json.dumps(value,ensure_ascii=False));tmp.chmod(0o600);tmp.replace(self.profile)
            return value

    def _verified_frame(self,chat):
        if not self.profile.exists():raise LinuxAdapterError('Choose and bind a chat first / 请先选择会话')
        saved=json.loads(self.profile.read_text());shot,meta=self.frame()
        if chat!=saved['chat'] or meta['chat']!=saved['chat'] or any(meta[k]!=saved[k] for k in ['avatar_sha256','chat_avatar_sha256','window_id','pid','size']):
            raise LinuxAdapterError('Account, chat or WeChat session changed; rebind in setup / 账号、会话或登录状态已变化，请重新绑定')
        return shot,meta,saved

    def snapshot(self,chat):
        with self.lock:
            shot,meta,saved=self._verified_frame(chat)
            x,y,w,h=meta['body'];body=shot.crop((x,y,x+w,y+h))
            digest=hashlib.sha256(body.tobytes()).hexdigest()
            if self.cached and self.cached[0]==digest:return self.cached[1]
            detections=self.vision.detect_objects(body,imgsz='auto');messages=[];skipped=[]
            items=sorted([d for d in detections if d['label'] in {'text','image','card','voice','video','file'} and d['confidence']>=.65],key=lambda d:d['pixel_bbox'][1])
            for i,d in enumerate(items):
                a,b,c,e=[int(round(t)) for t in d['pixel_bbox']]
                a=max(0,a);b=max(0,b);c=min(w,c);e=min(h,e)
                if c<=a or e<=b:continue
                sender='ME' if w-c<100 and a>100 else 'OTHER' if a<110 else 'UNKNOWN'
                crop=body.crop((a,b,c,e));text='';image=None
                if d['label']=='text':
                    reads=self.ocr.process_image(image=crop)
                    text='\n'.join(z['label'] for z in reads)
                    if not text:skipped.append({'row':i,'reason':'unreadable_text'});continue
                elif d['label']=='image':
                    crop.thumbnail((1000,1000));buf=io.BytesIO();crop.save(buf,format='PNG');image=base64.b64encode(buf.getvalue()).decode()
                else:skipped.append({'row':i,'reason':'unsupported_'+d['label']});continue
                names=[n for n in detections if n['label']=='name' and 0<=b-n['pixel_bbox'][3]<=70 and abs(n['pixel_bbox'][0]-a)<100]
                name=''
                if names and sender=='OTHER':
                    q=max(names,key=lambda n:n['pixel_bbox'][3])['pixel_bbox'];name=' '.join(z['label'] for z in self.ocr.process_image(image=body.crop(tuple(map(int,q)))))
                item={'sender':sender,'sender_name':name,'text':text,'kind':'image' if image else 'text','row_index':i,
                      'fingerprint':hashlib.sha256((sender+'\0'+name+'\0'+text+'\0'+(image or '')).encode()).hexdigest()}
                if image:item.update(image_base64=image,image_mime='image/png')
                messages.append(item)
            result={'ok':True,'chat':chat,'verified_chat':True,'chat_type':saved['kind'],
                    'messages':messages,'skipped':skipped,
                    'uncertainties':['visible_viewport_only','local_ocr_may_be_wrong','no_stable_wechat_message_id'],
                    'delivery_capabilities':{'text':True,'stickers':False}}
            self.cached=(digest,result);return result

    def chats(self):
        meta=self.observe()
        return {'ok':True,'chats':[{'name':meta['chat']}],'uncertainties':['current_open_chat_only']}

    def _clipboard(self,data=None):
        if data is None:
            p=subprocess.run(['xclip','-selection','clipboard','-o'],capture_output=True,timeout=2)
            return p.stdout if p.returncode==0 else b''
        subprocess.run(['xclip','-selection','clipboard','-i'],input=data,
                       stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True,timeout=2)

    def _editor(self,meta):
        x,y,w,h=meta['body'];bottom=900-60
        return [x+14,y+h+12,x+w-16,bottom]

    def _read_editor(self,meta):
        a,b,c,d=self._editor(meta)
        if d-b<20:raise LinuxAdapterError('Editor layout unavailable')
        self.command('xdotool','mousemove',a+50,(b+d)//2,'click','1')
        marker=('baguette-'+str(time.monotonic_ns())).encode();self._clipboard(marker)
        self.command('xdotool','key','--clearmodifiers','ctrl+a','ctrl+c');time.sleep(.12)
        copied=self._clipboard();self.command('xdotool','key','Right')
        return b'' if copied==marker else copied

    def send(self,chat,text):
        with self.lock:
            before=self.snapshot(chat);shot,meta,_=self._verified_frame(chat)
            previous=self._clipboard();attempted=False
            try:
                if self._read_editor(meta):raise LinuxAdapterError('Existing draft preserved / 输入框已有草稿，已保留')
                # Image/symbol drafts may have no copyable text. Reject visible ink.
                a,b,c,d=self._editor(meta);crop=shot.crop((a,b,c,d)).convert('RGB')
                import numpy as np
                px=np.asarray(crop,dtype='int16');bg=px[-2,-2];ink=(abs(px-bg).max(axis=2)>35)
                if int(ink.sum())>60:raise LinuxAdapterError('Editor contains visible content; draft preserved')
                self._clipboard(text.encode());self.command('xdotool','key','--clearmodifiers','ctrl+v');time.sleep(.15)
                if self._read_editor(meta).decode(errors='replace')!=text:
                    raise LinuxAdapterError('Composer readback differs; no send attempted')
                self._verified_frame(chat)
                from wechat_ai_bot.rpa.editor import enabled_send_button
                button=enabled_send_button(self.wm)
                if not button:raise LinuxAdapterError('No enabled Send button; draft preserved')
                attempted=True
                self.command('xdotool','mousemove',(button[0]+button[2])//2,(button[1]+button[3])//2,'click','1')
                for _ in range(5):
                    time.sleep(.35);self.cached=None;after=self.snapshot(chat)
                    if own_append(before['messages'],after['messages'],text) and not self._read_editor(meta):
                        return {'ok':True,'chat':chat,'verified_chat':True,'sent':True,'status':'observed'}
                return {'ok':False,'chat':chat,'verified_chat':True,'sent':False,'status':'uncertain','retry_allowed':False}
            except LinuxAdapterError:
                if attempted:return {'ok':False,'chat':chat,'sent':False,'status':'uncertain','retry_allowed':False}
                return {'ok':False,'chat':chat,'verified_chat':True,'sent':False,'status':'not_sent','retry_allowed':False}
            finally:self._clipboard(previous)

    def send_sticker(self,chat,sticker_id):
        return {'ok':False,'chat':chat,'sent':False,'status':'not_sent','retry_allowed':False,
                'error':'Linux Favorites sending requires its own calibration; no click attempted'}
