# Tester script
from contextlib import closing
import os
import sys
import xbmc
import xbmcaddon
import xbmcplugin
import xbmcvfs
import xbmcgui
import json
import urllib.parse

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

    if not cmd.addon_name:
        return
        
    addon_dir = xbmcaddon.Addon().getAddonInfo("path")
    dest_dir = os.path.abspath(os.path.join(addon_dir, os.pardir)) + f"/{cmd.addon_name}/"
    xbmcvfs.rmdir(dest_dir)
    xbmc.log(f"To {dest_dir}", xbmc.LOGINFO)

    src_dir = f"{cmd.source_dir}{cmd.addon_name}"
    xbmc.log(f"From {src_dir}", xbmc.LOGINFO)
    files = recursive_list_kodivfs_folders(src_dir, None)
    for file in files:
        dest_file = f"{dest_dir}{file}"
        src_file = f"{src_dir}/{file}"
        copied = xbmcvfs.copy(src_file, dest_file)
        xbmc.log(f"From {src_file} to {dest_file}. Succeeded: {copied}", xbmc.LOGINFO)

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
        return False
    
    selected_item:xbmcgui.ListItem = options[selection]
    path = selected_item.getPath()
    if path == "COPY":
        execute(cmd)
        return False
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
    return True

def list_addons(base_url, handle, addons):
    url_str = f"{base_url}?cmd=NEW"
    list_item = xbmcgui.ListItem("NEW")
    xbmcplugin.addDirectoryItem(handle = handle, url = url_str, listitem = list_item, isFolder = False)
    
    for addon_cmd in addons:
        list_item = xbmcgui.ListItem(addon_cmd.get_name())
        url_str = f"{base_url}?item={addon_cmd.get_name()}"
        xbmcplugin.addDirectoryItem(handle = handle, url = url_str, listitem = list_item, isFolder = False)
        
    xbmcplugin.endOfDirectory(handle = handle, succeeded = True, cacheToDisc = False)


def recursive_list_kodivfs_folders(fullPath, parentFolder):
    files = []
    subdirectories, filenames = xbmcvfs.listdir(fullPath)
    
    for filename in filenames:
        filePath = os.path.join(parentFolder, filename) if parentFolder is not None else filename
        files.append(filePath)

    for subdir in subdirectories:
        subPath = os.path.join(parentFolder, subdir) if parentFolder is not None else subdir
        subFullPath = os.path.join(fullPath, subdir)
        subPathFiles = recursive_list_kodivfs_folders(subFullPath, subPath)
        files.extend(subPathFiles)

    return files

def runplugin(base_url, addons, handle, args):
    list_addons(base_url, handle, addons)
    changed = False
    if 'cmd' in args and args['cmd'][0] == "NEW":
        cmd = AddonSourceCommand()
        addons.append(cmd)
        changed = cmd_dialog(cmd)

    if 'item' in args:
        i = args['item'][0]
        cmd = next((a for a in addons if a.addon_name == i), None)
        if cmd is not None:
            changed = cmd_dialog(cmd)

    if changed:
        data_dir = xbmcaddon.Addon().getAddonInfo('profile')
        path = data_dir + "addon_jobs.json"
        with closing(xbmcvfs.File(path, 'w')) as fo:
            cmds_dicts = [cmd.__dict__ for cmd in addons]
            fo.write(json.dumps(cmds_dicts))
    
base_url = sys.argv[0]
if len(sys.argv) > 1 and sys.argv[1].isdigit():
    handle = int(sys.argv[1])
else:
    handle = -1

addons = []
data_dir = xbmcaddon.Addon().getAddonInfo('profile')
xbmcvfs.mkdirs(data_dir)
path = data_dir + "addon_jobs.json"

if xbmcvfs.exists(path):
    xbmc.log(f"Open {path}", xbmc.LOGINFO)
    with closing(xbmcvfs.File(path, 'r')) as fo:
        jsonobjs = json.loads(fo.read())
        for jsonobj in jsonobjs:
            cmd = AddonSourceCommand()
            cmd.load(jsonobj)
            addons.append(cmd)

args = {}
if len(sys.argv) > 2 and sys.argv[2] != "":
    args = urllib.parse.parse_qs(sys.argv[2][1:])
    xbmc.log(f"ARGS: {args}", xbmc.LOGINFO)
    
runplugin(base_url, addons, handle, args)
