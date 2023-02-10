# Tester script
from contextlib import closing
import sys
import xbmc
import xbmcaddon
import xbmcplugin
import xbmcvfs
import xbmcgui
import json
import urllib.parse

addons = []

class AddonSourceCommand(object):
    
    def __init__(self):
        self.addon_name = ""
        self.source_dir = ""
        
    def get_name(self):
        return f"{self.addon_name}"
    
    def load(self, data: dict):
        for key, value in data.items():
            if key not in self.__dict__:
                continue
            if isinstance(self.__dict__[key], bool):
                self.__dict__[key] = bool(data[key])
            elif isinstance(self.__dict__[key], int):
                self.__dict__[key] = int(data[key])
            else:
                self.__dict__[key] = value
        
def execute(cmd: AddonSourceCommand):
    xbmc.log("Source files copy Starting ...", xbmc.LOGINFO)

    dest_dir = xbmcaddon.Addon(cmd.addon_name).getAddonInfo("path")
    xbmcvfs.rmdir(dest_dir)

    src_dir = f"{cmd.source_dir}/{cmd.addon_name}"
    xbmcvfs.copy(src_dir, dest_dir)

    xbmcgui.Dialog().notification("Copied", f"Copied addon {cmd.addon_name}", xbmcgui.NOTIFICATION_INFO)
    xbmc.executebuiltin('Container.Refresh')  

def cmd_dialog(cmd: AddonSourceCommand):    
    options = []
    options.append(xbmcgui.ListItem("Addon name", cmd.addon_name, "ADDONNAME"))
    options.append(xbmcgui.ListItem("Source parent dir", cmd.source_dir, "SRCDIR"))
    options.append(xbmcgui.ListItem("Copy", None, "COPY"))
    
    dialog = xbmcgui.Dialog()
    selection = dialog.select("COMMAND", options, useDetails=True)       
    if selection < 0: 
        return None
    
    selected_item:xbmcgui.ListItem = options[selection]
    path = selected_item.getPath()
    if path == "COPY":
        execute(cmd)
        list_addons()
        return
    elif path == "ADDONNAME":
        keyboard = xbmc.Keyboard(selected_item.getLabel2(), selected_item.getLabel())
        keyboard.doModal()
        if keyboard.isConfirmed():
            new_value = keyboard.getText()
            cmd.addon_name = new_value
    else:
        ret = xbmcgui.Dialog().browse(0, 'Source parent dir', '')
        if ret:
            cmd.source_dir = ret
    
    cmd_dialog(cmd)

def list_addons(base_url, handle):
    
    data_dir = xbmcaddon.Addon().getAddonInfo('profile')
    xbmcvfs.mkdirs(data_dir)
    path = data_dir + "/addon_jobs.json"
    
    addons_list = []
    if xbmcvfs.exists(path):
        with closing(xbmcvfs.File(path, 'r')) as fo:
            jsonobjs = json.loads(fo.read())
            for jsonobj in jsonobjs:
                cmd = AddonSourceCommand()
                cmd.load(jsonobj)
                addons_list.append(cmd)

    url_str = f"{base_url}?cmd=NEW"
    list_item = xbmcgui.ListItem("NEW")
    xbmcplugin.addDirectoryItem(handle = handle, url = url_str, listitem = list_item, isFolder = False)
    
    for addon_cmd in addons_list:
        list_item = xbmcgui.ListItem(addon_cmd.get_name())
        url_str = f"{base_url}?item={addon_cmd.get_name()}"
        xbmcplugin.addDirectoryItem(handle = handle, url = url_str, listitem = list_item, isFolder = False)
        
    xbmcplugin.endOfDirectory(handle = handle, succeeded = True, cacheToDisc = False)

def runplugin(base_url, handle, args):
    list_addons(base_url, handle)
    if 'cmd' in args and args['cmd'][0] == "NEW":
        cmd = AddonSourceCommand()
        addons.append(cmd)
        cmd_dialog(cmd)

    if 'item' in args:
        i = args['item'][0]
        cmd = next((a for a in addons if a.addon_name == i), None)
        cmd_dialog(cmd)

    data_dir = xbmcaddon.Addon().getAddonInfo('profile')
    path = data_dir + "/addon_jobs.json"
    with closing(xbmcvfs.File(path, 'w')) as fo:
        cmds_dicts = [cmd.__dict__ for cmd in addons]
        fo.write(json.dumps(cmds_dicts))
            
try:
    addons = []
    base_url = sys.argv[0]
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        handle = int(sys.argv[1])
    else:
        handle = -1

    args = {}
    if len(sys.argv) > 2 and sys.argv[2] != "":
        args = urllib.parse.parse_qs(sys.argv[2][1:])
        xbmc.log(f"ARGS: {args}", xbmc.LOGINFO)
        
    runplugin(base_url, handle, args)
except Exception as ex:
    xbmc.log(f"General exception: {ex.message}", xbmc.LOGERROR)
