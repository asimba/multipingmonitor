#!/usr/bin/env python
# -*- coding: utf-8 -*-

from sys import argv,exit,getfilesystemencoding
from subprocess import Popen,PIPE,STDOUT
from threading import Thread,enumerate
from time import sleep
import signal
from platform import system
if system()=='Windows': osflag=False
else:
    import select
    from fcntl import flock,LOCK_UN,LOCK_NB,LOCK_EX
    osflag=True
from string import count
from os import getcwd,mkdir,remove,getpid,kill
from os.path import abspath,join,realpath,basename,isfile
from hashlib import sha1
from tempfile import gettempdir
from shutil import rmtree
import locale,pickle,base64,zlib

def errmsg(msg):
    if osflag:
        try:
            f=Popen(['notify-send',msg],False,stdin=None,stdout=None,\
            stderr=None)
            f.wait()
        except: pass
        try:
            f=Popen(['xmessage',msg],False,stdin=None,stdout=None,stderr=None)
            f.wait()
        except: pass
    else:
        import ctypes
        MessageBox=ctypes.windll.user32.MessageBoxW
        MessageBox(0,unicode(msg),u'Error!',16)

try: import wx
except:
    _MSG="Please install wxPython 2.8 or higher (http://www.wxpython.org/)!\n\
Under Debian or Ubuntu you may try: sudo aptitude install python-wxgtk2.8"
    errmsg(_MSG)
    raise RuntimeError(_MSG)

EVT_PINGMSG_ID=wx.NewId()
EVT_ERRPING_ID=wx.NewId()
EVT_CLOSEPINGMSG_ID=wx.NewId()

class PMsgEvent(wx.PyEvent):
    def __init__(self,data,evt):
        wx.PyEvent.__init__(self)
        self.SetEventType(evt)
        self.data=data

class ping(Thread):
    def __init__(self, host):
        Thread.__init__(self)
        self.cmd=['ping']
        if not osflag: self.cmd.append('-t')
        self.cmd.append(host)
        self.retries=0
        self.host=host
        self.stop_flag=False

    def run(self):
        try:
            if osflag:
                proc=Popen(self.cmd,shell=False,stdin=None,stdout=PIPE,\
                    stderr=STDOUT,bufsize=0)
            else:
                from subprocess import STARTUPINFO
                si=STARTUPINFO()
                si.dwFlags|=1
                si.wShowWindow=0
                proc=Popen(self.cmd,shell=False,stdin=None,stdout=PIPE,\
                    stderr=STDOUT,bufsize=0,startupinfo=si)
            while 1:
                if self.stop_flag:
                    if osflag: proc.send_signal(signal.SIGKILL)
                    else: proc.kill()
                    break
                if osflag:
                    if proc.stdout in select.select([proc.stdout],[],[],1)[0]:
                        line=proc.stdout.readline()
                    else: line=' \n'
                else: line=proc.stdout.readline()
                if not len(line): break
                else:
                    if count(line,'ttl') or count(line,'TTL'): self.retries=0
                    else: self.retries=self.retries+1
                    line=' '
                sleep(0.5)
            proc.poll()
        except: pass

    def abort(self): self.stop_flag=True

class ping_threads(Thread):
    def __init__(self,hosts,window):
        Thread.__init__(self)
        self.hosts=hosts
        self.pings=[]
        self.window=window
        self.stop_flag=False

    def run(self):
        for h in self.hosts: self.pings.append(ping(h))
        for p in self.pings:
            p.start()
            sleep(0.5)
            if not p.isAlive():
                self.stop_flag=True
                wx.PostEvent(self.window,PMsgEvent(p.host,EVT_ERRPING_ID))
        while 1:
            if not self.stop_flag:
                alive=False
                for p in self.pings:
                    p.join(1)
                    if p.isAlive():
                        alive=True
                        if p.retries>=5:
                            wx.PostEvent(self.window,PMsgEvent(p.host,\
                                EVT_PINGMSG_ID))
                        else:
                            wx.PostEvent(self.window,PMsgEvent(p.host,\
                                EVT_CLOSEPINGMSG_ID))
                if not alive:
                    wx.CallAfter(self.window.Close)
                    break
            else:
                for p in self.pings:
                    if p.isAlive():
                        p.abort()
                        p.join()
                break

    def abort(self): self.stop_flag=True

class pingmsg(wx.Dialog):
    def __init__(self,message,host,window):
        self.__init__(message,host,window,None,-1,"")

    def __init__(self,message,host,window,*args,**kwds):
        kwds["style"]=wx.CAPTION|wx.CLOSE_BOX|wx.MINIMIZE_BOX|wx.SYSTEM_MENU|\
            wx.FRAME_NO_TASKBAR|wx.STAY_ON_TOP
        wx.Dialog.__init__(self,None,**kwds)
        self.label=wx.StaticText(self,-1,message,style=wx.ALIGN_CENTRE)
        self.button=wx.Button(self,-1,"Ok")
        self.__set_properties()
        self.__do_layout()
        self.window=window
        self.host=host
        self.Bind(wx.EVT_BUTTON,self.closemsgbox,self.button)
        self.Bind(wx.EVT_CLOSE,self.closemsgbox)

    def __set_properties(self):
        self.SetTitle("")
        self.SetSize((372,114))
        self.SetBackgroundColour(\
            wx.SystemSettings_GetColour(wx.SYS_COLOUR_WINDOW))

    def __do_layout(self):
        frame_sizer=wx.BoxSizer(wx.VERTICAL)
        label_sizer=wx.BoxSizer(wx.VERTICAL)
        frame_sizer.Add((20,20),0,wx.EXPAND,0)
        label_sizer.Add(self.label,0,wx.ALIGN_CENTER_HORIZONTAL|\
            wx.ALIGN_CENTER_VERTICAL,0)
        frame_sizer.Add(label_sizer,1,wx.EXPAND,0)
        frame_sizer.Add((20,10),0,wx.EXPAND,0)
        frame_sizer.Add(self.button,0,wx.ALIGN_CENTER_HORIZONTAL|\
            wx.ALIGN_CENTER_VERTICAL,0)
        frame_sizer.Add((20,10),0,wx.EXPAND,0)
        self.SetSizer(frame_sizer)
        self.Layout()
        self.Centre()

    def closemsgbox(self, event):
        del self.window.msgs[self.host]
        self.Destroy()

class translator():
    def __init__(self):
        self.voc={}
        self.locale=locale.getdefaultlocale()

    def find(self,key):
        if self.voc.has_key(key):
            if self.voc[key].has_key(self.locale[0]):
                return self.voc[key][self.locale[0]].encode(self.locale[1])
        return key

t=translator()

t.voc=pickle.loads(zlib.decompress(base64.decodestring("\
eNqFU81u2zAMvvspmF7c02DLcpycetptp6XtLgMGWbYTA5ktyA6KvH0pUom5ZG0vTCxR/H5IPjYu\
S3bpd+9HD2+H/tiCPw1DP+zBhdDh8WGc5jRxefLYOIXJ/vTn5wseFMnr71Om8zZEvQmx4JhTNBQz\
oJ+OkjJO4qOK78V1QVG+LpkG/dcUa8rpYHkQC9VcLnE6mabdw67fD+Z4FQDpQ+LKIGGd7CNzxUiK\
Ky6ltOXq+UcgpLiwgCZUAYz9W+HnJiBsrwhfebNCWzOqsLO+dzP0E5ijb01zvvRhBc/+DPMI0zy6\
p9AHakSuFhDpLVMrxAlHK2Imda2jz5+2ZMtJFJtIHYRAEqWVeN0INmqRzznaPqGOgoS/DMba1s2m\
xtmzB+ONnVsP/YCCPeoPijUpLhfFjeCjBdLdGGmBzeo1t3ALYtbEdSTL5Wp2RcFtwX/MjpOKPNek\
6Jfx1LjAvCLmm4W5Eu5I2OzuvAzDsb14FNzBIQijAR2uKRZXGW1k/n9bpI5KALWi67FJ9xvKXa1u\
+8YsLz1kV7Sgz2NSIzVFO5iGeT7i9q1w+VRBdDXRTQVmRFMLeWYRV7K5rooqyY0fPa7z2NFaTwGh\
/evmc7BbrQmiut3wTgjJZec+X3AFHw1VILNBMt/eAQtZel0=\
")))

def _(s):
    return t.find(s)

class empty(wx.Frame):
    def __init__(self, *args, **kwds):
        wx.Frame.__init__(self, *args, **kwds)
        self.Bind(wx.EVT_CLOSE,self.OnClose)
        self.Bind(wx.EVT_END_SESSION,self.OnClose)
        self.Connect(-1,-1,EVT_ERRPING_ID,self.OnErrPing)
        self.Connect(-1,-1,EVT_PINGMSG_ID,self.OnPingMsg)
        self.Connect(-1,-1,EVT_CLOSEPINGMSG_ID,self.OnClosePingMsg)
        self.__set_properties()
        self.__do_layout()
        self.msgs={}
        self.pings=None

    def __set_properties(self): self.SetTitle("")

    def __do_layout(self): self.Layout()

    def start(self,hosts):
        self.pings=ping_threads(hosts,self)
        self.pings.start()

    def OnErrPing(self,event):
        if event.data:
            wx.MessageBox(_("Error while running ping for host")+\
                " '%s' !" % event.data,_('Error!'),wx.OK|wx.ICON_ERROR)
        else: pass
        self.OnClose(event)

    def OnPingMsg(self,event):
        if event.data:
            msg=_("Signal for host '")+event.data+_("' is lost!")
            if not self.msgs.has_key(event.data):
                self.msgs[event.data]=pingmsg(msg,event.data,self)
                self.msgs[event.data].Show()
                wx.CallAfter(self.msgs[event.data].RequestUserAttention)
        else: pass

    def OnClosePingMsg(self,event):
        if event.data:
            if self.msgs.has_key(event.data):
                self.msgs[event.data].closemsgbox(event.data)
        else: pass

    def OnClose(self,event):
        for m in list(self.msgs.values()): m.Destroy()
        if self.pings.isAlive():
            self.pings.abort()
            self.pings.join()
        self.Destroy()

class app(wx.App):
    def SetBase(self,base): self.base=base

    def OnExit(self):
        try: self.base.OnClose()
        except: pass

def start_pings(hosts,lockfile):
    dumb=app(0)
    base=empty(None,-1,"")
    dumb.SetTopWindow(base)
    dumb.SetBase(base)
    global wnd
    wnd=base
    if not osflag:
        lockfile.seek(0)
        lockfile.write(str(base.GetHandle()))
        lockfile.flush()
    base.start(hosts)
    dumb.MainLoop()

def load_hosts():
    hosts=[]
    fn='hosts.list'
    try:
        f=open(join(abspath(getcwd()),fn),'r')
        for l in f:
            l=l.strip()
            if len(l) and l[0]!='#': hosts.append(l.strip())
        f.close()
    except:
        app=wx.App(0)
        wx.MessageBox(_('Unable to read file')+" '%s'" % fn,\
            _('Error!'),wx.OK|wx.ICON_ERROR)
        exit()
    if not len(hosts):
        app=wx.App(0)
        wx.MessageBox(_('List of hosts is empty!'),_('Error!'),\
            wx.OK|wx.ICON_ERROR)
        exit()
    for h in hosts:
        if any((c in ';,/\\ ?*|\n\r\t\f\'\"\v') for c in h):
            app=wx.App(0)
            wx.MessageBox(_('Unacceptable character in string')+\
                ": '%s'" % h,_('Error!'),\
                wx.OK|wx.ICON_ERROR)
            exit()
    return hosts

class _lockfile():
    def __init__(self):
        self.file=None
        hasher=sha1()
        ifile=open(realpath(argv[0]),'rb')
        while True:
            buf=ifile.read(0x800000)
            if len(buf)==0: break
            hasher.update(buf)
        ifile.close()
        self.hash=hasher.hexdigest()
        self.lockdir=join(gettempdir(),basename(argv[0]))
        try: mkdir(self.lockdir)
        except: pass
        self.lockfile=join(self.lockdir,self.hash+'.lock')
        if osflag: self.pidfile=join(self.lockdir,self.hash+'.pid')
        else: self.pidfile=self.lockfile
        if isfile(self.lockfile):
            if not osflag:
                try: remove(self.lockfile)
                except: return
        try: self.file=open(self.lockfile,'wb')
        except:
            self.file=None
            return
        if osflag:
            try: flock(self.file,LOCK_NB|LOCK_EX)
            except:
                self.file.close()
                self.file=None
                return
        try:
            self.file.write(str(getpid()))
            self.file.flush()
            if osflag:
                try:
                    pfile=open(self.pidfile,'wb')
                    pfile.write(str(getpid()))
                    pfile.flush()
                    pfile.close()
                except: pass
        except:
            if osflag:
                try: flock(self.file,LOCK_UN)
                except: pass
            self.file.close()
            self.file=None
            return

    def __del__(self):
        if self.file:
            if osflag:
                try: flock(self.file,LOCK_UN)
                except: pass
            self.file.close()
            rmtree(self.lockdir,ignore_errors=True)

class lockfile():
    def __init__(self): self.lock=_lockfile()

    def acquired(self): return True if self.lock.file else False

    def getfilepid(self):
        ifile=open(self.lock.pidfile,'rb')
        f=int(ifile.read())
        ifile.close()
        return int(f)

if osflag:
    def signalhandler(signum,frame): wx.CallAfter(wnd.Close)

if __name__ == "__main__":
    _lock=lockfile()
    if _lock.acquired():
        if osflag: signal.signal(signal.SIGUSR1,signalhandler)
        start_pings(load_hosts(),_lock.lock.file)
    else:
        pid=_lock.getfilepid()
        app=wx.App(0)
        res=wx.MessageBox(_('Script is already running! Try to stop?'),\
            _('Warning!'),wx.YES_NO|wx.ICON_WARNING)
        if res==wx.YES:
            if osflag: kill(pid,signal.SIGUSR1)
            else:
                import ctypes
                SendMessage=ctypes.windll.user32.SendMessageW
                SendMessage(pid,0x0010,0,0)
