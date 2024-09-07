import glob
import json
import ssl
import os
import pprint
import re
import shutil
import subprocess
import urllib.request
from string import Template
from datetime import datetime, timedelta
import time

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36"  # noqa: E501

ARMA_ROOT="/arma3"
#SHARE_ARMA_ROOT="/var/run/share/arma3"
COMMON_SHARE_ARMA_ROOT="/var/run/share/arma3/server-common"
THIS_SHARE_ARMA_ROOT="/var/run/share/arma3/this-server"
STEAM_ROOT="/steamcmd"

FOLDER_KEYS = ARMA_ROOT+"/keys"
FOLDER_MODS = ARMA_ROOT+"/mods"
FOLDER_SERVERMODS = ARMA_ROOT+"/servermods"
FOLDER_ADDONS = ARMA_ROOT+"/addons"
FOLDER_CONFIG = ARMA_ROOT+"/config"
FOLDER_USERCONFIG = ARMA_ROOT+"/userconfig"
FOLDER_MPISSIONS = ARMA_ROOT+"/mpmissions"

CONFIG_FILE = FOLDER_CONFIG+os.sep+os.environ["ARMA_CONFIG"]
SERVER_BASE = ARMA_ROOT+os.sep+os.environ["BASIC_CONFIG"]
PARAM_FILE = FOLDER_CONFIG+os.sep+os.environ["PARAM_CONFIG"]
PRESET_FILE=FOLDER_CONFIG+os.sep+os.environ["MODS_PRESET"]
JSON_CONFIG = FOLDER_CONFIG+os.sep+"server.json"
WORKSHOP_DIR="/tmp"+os.sep+"steamapps/workshop/content/107410"+os.sep

# 1. /arma3/* ordner von "außen" löschen
# 2. /tmp/workshop/.../mods/xxx Ornder von this-server und common-server hierher linken
#                                      fehlende order in common-server anlegen und linken
# 

NEW_MOD_LIST=[]
NEW_SRVMOD_LIST=[]
NEW_MAPS_LIST=[]
WORK_MODS="mods"
WORK_SMODS="servermods"

def logdebug(what, silent=False):
    if not silent:
        print("logdebug  : {}".format(what), flush=True)
def lognotice(what, silent=False):
    if not silent:
        print("NOTICE : {}".format(what), flush=True)
def logwarning(what, silent=False):
    if not silent:
        print("WARNING: {}".format(what), flush=True)
def logerror(what, silent=False):
    if not silent:
        print("ERROR  : {}".format(what), flush=True)

def mod_param(name, mods):
    return ' -{}="{}" '.format(name, ";".join(mods))

def check_double_mods(mod_list):
    e=[]
    id=[]
    name=[]
    r=True
    for dispname, steamid in mod_list:
        if not dispname in name and not steamid in id:
            e.append([dispname, steamid])
            id.append(steamid)
            name.append(dispname)
        elif not steamid in id and dispname in name:
            logerror("modname {} is used multiple times".format(dispname))
            r=False
        else:
            logerror("steamid {} is used multiple times".format(steamid))
            r=False
    return r,e

def env_defined(key):
    return key in os.environ and len(os.environ[key]) > 0

def make_sure_dir(path, silent=False):
    if not os.path.isdir(path):
        if os.path.exists(path):
            logwarning("{} is not a dir, removing".format(path))
            os.remove(path)
        os.makedirs(path)
        lognotice("{} created".format(path), silent)
    else:
        logerror("{} is a file and not a path".format(path))

def link_it(what, to, silent=False):
    if not os.path.exists(to):
        try:
            os.symlink(what, to)
            lognotice("{} linked to {}".format(what, to), silent=silent)
        except:
            logerror("{} failed to link to {}".format(what, to))
    else:
        logwarning("{} exists, cannot link {}".format(to, what))

def copy_key(moddir, keyfolder, steamid, dispname=""):
    keys = glob.glob(os.path.join(moddir, "**/*.bikey"), recursive=True)
    if len(keys) > 0:
        for key in keys:
            if not os.path.isdir(key):
                shutil.copy2(key, keyfolder+os.sep+steamid+"_"+os.path.basename(key))
    else:
        logwarning("Missing keys: {} ({}), {}: {}".format(moddir, dispname, os.path.join(moddir, "**/*.bikey"), keys))
        
def fix_folder_characters(path):
    for subdir, dirs, files in os.walk(path):
        for file in files:
            if file.lower()!=file and (file.endswith(".pbo") or file.endswith(".paa") or file.endswith(".sqf")):
                #lognotice("to lower FILE: {} -> {}".format(subdir + os.sep + file, file.lower()))
                #os.rename(subdir + os.sep + file, subdir + os.sep + file.lower())

                for sfile in files:
                    if sfile.startswith(file) and sfile.lower() != sfile:
                        lognotice("to lower FILE: {} -> {}".format(subdir + os.sep + sfile, sfile.lower()))
                        os.rename(subdir + os.sep + sfile, subdir + os.sep + sfile.lower())
                        
        for dir in dirs:
            if dir!=dir.lower():
                lognotice("to lower DIR: {} -> {}".format(subdir + os.sep + dir, subdir + os.sep + dir.lower()))
                os.rename(subdir + os.sep + dir, subdir + os.sep + dir.lower())
            fix_folder_characters(subdir + os.sep + dir.lower())

def get_last_update(steamid):
    dt_1=datetime.now()
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    url_string="https://steamcommunity.com/sharedfiles/filedetails/"+str(steamid)
    dt_2=datetime.now()
    req = urllib.request.Request(url_string, headers={"User-Agent": USER_AGENT})
    remote = urllib.request.urlopen(req)
    html=remote.read().decode(remote.headers.get_content_charset());
    #html=html.split("detailsStatsContainerRight",1)[1].split("detailsStatsContainerRight",1)[0]
    dt_3=datetime.now()
    
    regex=r"\"detailsStatRight\".*>(.*)<.*\/div.*>"
    matches=re.findall(regex, html, re.MULTILINE)

    dt=datetime.now().replace(year=1984)
    dt_4=datetime.now()
    if len(matches)==2:
        
        try:
            dt=datetime.strptime(matches[1], "%d %b, %Y @ %I:%M%p")
        except ValueError:
            dt=datetime.strptime(matches[1], "%d %b @ %I:%M%p")
            dt=dt.replace(year=datetime.now().year)
        #lognotice("mod release time: {}".format(dt))
        #dt_5=datetime.now()
        #lognotice("time: {},{},{},{}".format(dt_2-dt_1, dt_3-dt_2, dt_4-dt_3, dt_5-dt_4 ))
        return dt
    elif len(matches)==3:    
        try:
            dt=datetime.strptime(matches[2], "%d %b, %Y @ %I:%M%p")
        except ValueError:
            dt=datetime.strptime(matches[2], "%d %b @ %I:%M%p")
            dt=dt.replace(year=datetime.now().year)
        #lognotice("mod update time: {}".format(dt))
        #dt_5=datetime.now()
        #lognotice("time: {},{},{},{}".format(dt_2-dt_1, dt_3-dt_2, dt_4-dt_3, dt_5-dt_4 ))
        return dt
        
    logerror("failed to find any release or update date, using fallback-default of {}".format(dt.strftime("%Y-%m-%d %H:%M:%S")))
    return dt          

def startup_folder_clean_prepare():
    to_unlink=[]
    to_rmtree=[]
    to_ignore=[]

    for item in os.listdir(ARMA_ROOT):
        if item == "steamapps" or item == "battleye":
            continue
        if os.path.islink(item):
            to_unlink.append(item)
        elif os.path.isdir(item):
            to_rmtree.append(item)
        else:
            to_ignore.append(item)
    if os.path.exists(WORKSHOP_DIR):
        to_rmtree.append(WORKSHOP_DIR)

    logdebug("unlinking {}".format(to_unlink))
    for item in to_unlink:
        os.unlink(item)
    logdebug("removing {}".format(to_rmtree))
    for item in to_rmtree:
        shutil.rmtree(item)

    logwarning("ignoring {}".format(to_ignore))

    to_make=[]
    to_link=[]
    to_make.append(FOLDER_KEYS)
    to_make.append(FOLDER_MODS)
    to_make.append(FOLDER_SERVERMODS)
    to_make.append(WORKSHOP_DIR)

    to_link.append([THIS_SHARE_ARMA_ROOT+"/config", ARMA_ROOT+"/config"])
    to_link.append([THIS_SHARE_ARMA_ROOT+"/userconfig", ARMA_ROOT+"/userconfig"])
    to_link.append([THIS_SHARE_ARMA_ROOT+"/logs", ARMA_ROOT+"/logs"])
    to_link.append([COMMON_SHARE_ARMA_ROOT+"/basic.cfg", ARMA_ROOT+"/basic.cfg"])
    if os.path.exists(THIS_SHARE_ARMA_ROOT+"/mpmissions"):
        to_link.append([THIS_SHARE_ARMA_ROOT+"/mpmissions", ARMA_ROOT+"/mpmissions"])
    
    logdebug("creating {}".format(to_make))
    for item in to_make:
        make_sure_dir(item, silent=True)
    logdebug("linking {}".format(to_link))
    for item_from, item_to in to_link:
        link_it(item_from, item_to, silent=True)

def parse_json_config(): # bool
    global SERVER_BASE
    global PARAM_FILE
    global CONFIG_FILE
    global PRESET_FILE
    global NEW_SRVMOD_LIST
    global NEW_MOD_LIST
    global NEW_MAPS_LIST

    jconfig=None
    if os.path.exists(JSON_CONFIG):
        lognotice("found server.json override file")
        with open(JSON_CONFIG) as f:
            try:
                jconfig = json.load(f)
            except:
                logerror("failed to load {}".format(JSON_CONFIG))
                return False

    if not jconfig is None:
        active_jcname=jconfig.get("config-name", None);
        debug_skip_install=jconfig.get("debug_skip_install", False)
        if debug_skip_install:
            logwarning("skipping arma3 install and update - use at own risk!")

        if not active_jcname is None:
            lognotice("config {} is selected in json file".format(active_jcname))
            active_jc=jconfig.get("configs",{}).get(active_jcname, None)
            if not active_jc is None:
                if "server-config-file" in active_jc:
                    lognotice("overwrite ARMA_CONFIG with {}".format(active_jc["server-config-file"]))
                    os.environ["ARMA_CONFIG"] = active_jc["server-config-file"]
                    CONFIG_FILE = FOLDER_CONFIG+os.sep+os.environ["ARMA_CONFIG"]
                if "server-parameters" in active_jc:
                    lognotice("overwrite ARMA_PARAMS with {}".format(active_jc["server-parameters"]))
                    os.environ["ARMA_PARAMS"] = active_jc["server-parameters"]
                    PARAM_FILE = "/does-not-exist"
                if "server-base-file" in active_jc:
                    lognotice("overwrite BASIC_CONFIG with {}".format(active_jc["server-base-file"]))
                    os.environ["BASIC_CONFIG"] = active_jc["server-base-file"]
                    SERVER_BASE = FOLDER_CONFIG+os.sep+os.environ["BASIC_CONFIG"]

                modresult=True
                if "servermods" in active_jc:
                    NEW_SRVMOD_LIST=active_jc["servermods"]
                    r,NEW_SRVMOD_LIST=check_double_mods(NEW_SRVMOD_LIST)
                    if not r:
                        modresult=False
                    else:
                        for i in range(len(NEW_SRVMOD_LIST)):
                            NEW_SRVMOD_LIST[i][0]=NEW_SRVMOD_LIST[i][0].replace(":","-").replace("/","_").replace("\\","_").rstrip(".,")
                        
                if "mods" in active_jc:
                    NEW_MOD_LIST=active_jc["mods"]
                    r,NEW_MOD_LIST=check_double_mods(NEW_MOD_LIST)
                    if not r:
                        modresult=False
                    else:
                        for i in range(len(NEW_MOD_LIST)):
                            NEW_MOD_LIST[i][0]=NEW_MOD_LIST[i][0].replace(":","-").replace("/","_").replace("\\","_").rstrip(".,")
                if "maps" in active_jc:
                    NEW_MAPS_LIST=active_jc["maps"]
                    r,NEW_MAPS_LIST=check_double_mods(NEW_MAPS_LIST)
                    if not r:
                        modresult=False
                    else:
                        for i in range(len(NEW_MAPS_LIST)):
                            NEW_MAPS_LIST[i][0]=NEW_MAPS_LIST[i][0].replace(":","-").replace("/","_").replace("\\","_").rstrip(".,")

                if not modresult:
                    return False

                if "mod-config-file" in active_jc:
                    lognotice("overwrite MODS_PRESET with {}".format(active_jc["mod-config-file"]))
                    os.environ["MODS_PRESET"] = active_jc["mod-config-file"]
                    PRESET_FILE = FOLDER_CONFIG+os.sep+os.environ["MODS_PRESET"]
                if "num-headless" in active_jc:
                    lognotice("overwrite HEADLESS_CLIENTS with {}".format(active_jc["num-headless"]))
                    os.environ["HEADLESS_CLIENTS"]=str(active_jc["num-headless"])
                if not active_jc.get("creator-dlc", None) is None:
                    if active_jc["creator-dlc"].get("enable-creator", False):
                        os.environ["STEAM_BRANCH"]="creatordlc"
                        os.environ["STEAM_BRANCH_PASSWORD"]=""
                        os.environ["ARMA_CDLC"]=""
                    if active_jc["creator-dlc"].get("csla-iron-curtain", False):
                        if len(os.environ["ARMA_CDLC"]) > 0:
                            os.environ["ARMA_CDLC"]+=";"
                        os.environ["ARMA_CDLC"]+="csla"
                    if active_jc["creator-dlc"].get("global-mobilization-cold-war", False):
                        if len(os.environ["ARMA_CDLC"]) > 0:
                            os.environ["ARMA_CDLC"]+=";"
                        os.environ["ARMA_CDLC"]+="gm"
                    if active_jc["creator-dlc"].get("s.o.g.-prairie-fire", False):
                        if len(os.environ["ARMA_CDLC"]) > 0:
                            os.environ["ARMA_CDLC"]+=";"
                        os.environ["ARMA_CDLC"]+="vn"
                    if active_jc["creator-dlc"].get("western-sahara", False):
                        if len(os.environ["ARMA_CDLC"]) > 0:
                            os.environ["ARMA_CDLC"]+=";"
                        os.environ["ARMA_CDLC"]+="ws"
                    if active_jc["creator-dlc"].get("spearhead-1944", False):
                        if len(os.environ["ARMA_CDLC"]) > 0:
                            os.environ["ARMA_CDLC"]+=";"
                        os.environ["ARMA_CDLC"]+="spe"
            else:
                logerror("no config entry with key {} found in json file".format(active_jcname))
                return False
        else:
            logerror("no parameter \"config-name\" set in config")
            return False
    return True

def link_external_share_with_workshop(): # bool
    
    link_servermods=[]
    link_mods=[]
    link_maps=[]
    workshop_download=[]
    workshop_download_t0=[]
    result=True

    srvmod_path=THIS_SHARE_ARMA_ROOT+os.sep+"servermods"+os.sep
    lognotice("workshop - servermods: {}".format(NEW_SRVMOD_LIST))
    for dispname, steamid in NEW_SRVMOD_LIST:
        if not os.path.exists(srvmod_path+steamid):
            os.makedirs(srvmod_path+steamid)
            with open(srvmod_path+steamid+"_@"+dispname, "w") as f:
                f.write("")
        link_servermods.append([dispname, srvmod_path+steamid, WORKSHOP_DIR+os.sep+steamid])
        workshop_download.append([dispname, steamid])

    priv_mod_path=THIS_SHARE_ARMA_ROOT+os.sep+"mods"+os.sep
    pub_mod_path=COMMON_SHARE_ARMA_ROOT+os.sep+"mods"+os.sep
    lognotice("workshop - mods: {}".format(NEW_MOD_LIST))
    for dispname, steamid in NEW_MOD_LIST:
        if os.path.exists(priv_mod_path+steamid):
            link_mods.append([dispname, priv_mod_path+steamid, WORKSHOP_DIR+os.sep+steamid])
        elif not os.path.exists(pub_mod_path+steamid):
            os.makedirs(pub_mod_path+steamid)
            with open(pub_mod_path+steamid+"_@"+dispname, "w") as f:
                f.write("")
            link_mods.append([dispname, pub_mod_path+steamid, WORKSHOP_DIR+os.sep+steamid])
        else:
            link_mods.append([dispname, pub_mod_path+steamid, WORKSHOP_DIR+os.sep+steamid])
        workshop_download.append([dispname, steamid])

    map_path=COMMON_SHARE_ARMA_ROOT+os.sep+"maps"+os.sep
    lognotice("workshop - maps: {}".format(NEW_MAPS_LIST))
    for dispname, steamid in NEW_MAPS_LIST:
        if not os.path.exists(map_path+steamid):
            os.makedirs(map_path+steamid)
            with open(map_path+steamid+"_@"+dispname, "w") as f:
                f.write("")
        link_maps.append([dispname, map_path+steamid, WORKSHOP_DIR+os.sep+steamid])
        workshop_download.append([dispname, steamid])

    logdebug("linking servermods to workshop {}".format(link_servermods))
    for _, item_from, item_to in link_servermods:
        link_it(item_from, item_to, silent=True)
    
    logdebug("linking mods to workshop {}".format(link_mods))
    for _, item_from, item_to in link_mods:
        link_it(item_from, item_to, silent=True)

    logdebug("linking maps to workshop {}".format(link_maps))
    for _, item_from, item_to in link_maps:
        link_it(item_from, item_to, silent=True)
    
    # now all mods are linked to the workshop folder, regardless if already downloaded or not
    # we'll now check for updates or if folder is empty and download if necessary

    for dispname, steamid in workshop_download:
        up_dt=get_last_update(steamid)
        act_dt=datetime.now().replace(year=1984)
        datecfg=WORKSHOP_DIR+os.sep+steamid+os.sep+"srvdon_info.cfg"
        if not os.path.exists(datecfg):
            with open(datecfg, "w") as f:
                f.write(act_dt.strftime("%Y-%m-%d %H:%M:%S"))
        else:
            try:
                with open(datecfg, "r") as f:
                    act_dt=datetime.strptime(f.read(), "%Y-%m-%d %H:%M:%S")
            except ValueError:
                logerror("failed to get update time from {}".format(datecfg))
                os.remove(datecfg)
                result=False

        if len(os.listdir(WORKSHOP_DIR+os.sep+steamid)) < 2:
            workshop_download_t0.append([dispname, steamid, act_dt, up_dt])
        elif up_dt > act_dt:
            workshop_download_t0.append([dispname, steamid, act_dt, up_dt])

    # now we have all mods with empty folder or with an update
    logdebug("downloading or updating mods: {}".format(workshop_download_t0))
    for dispname, steamid, file_dt, remote_dt in workshop_download_t0:
        retry_count=12
        returncode=-1
        while returncode!=0 and retry_count > 0:
            if returncode==5:
                logwarning("Rate Limit Exceeded, sleeping 3 minutes and try again")
                time.sleep(180)
            elif returncode==10:
                logwarning("Timeout during download, will try again in 30 seconds")
                time.sleep(30)
            
            steamcmd = ["/steamcmd/steamcmd.sh"]
            steamcmd.extend(["+force_install_dir", "/tmp"])
            steamcmd.extend(["+login", os.environ["STEAM_USER"], os.environ["STEAM_PASSWORD"]])
            steamcmd.extend(["+workshop_download_item", "107410", steamid, "validate"])
            steamcmd.extend(["+quit"])
            logwarning("previous download of {} ({}) timed out, try again".format(dispname, steamid))
            returncode=subprocess.run(steamcmd).returncode
            retry_count=retry_count-1

        datecfg=WORKSHOP_DIR+os.sep+steamid+os.sep+"srvdon_info.cfg"    
        if returncode!=0:
            logerror("download of {} ({}) failed".format(dispname, steamid))
            if os.path.exists(datecfg):
                os.unlink(datecfg)
            os.unlink(WORKSHOP_DIR+os.sep+steamid)
            result=False
        else:
            with open(datecfg, "w") as f:
                f.write(remote_dt.strftime("%Y-%m-%d %H:%M:%S"))
                lognotice("updated mod update time of {} ({}) to {}".format(dispname, steamid, up_dt.strftime("%Y-%m-%d %H:%M:%S")) )


    # as last step we have to sanitize the folder names, extract all server keys and link those with
    # a proper name to the arma3 folder
    for dispname, steamid in workshop_download:
        fix_folder_characters(WORKSHOP_DIR+os.sep+steamid)
        copy_key(WORKSHOP_DIR+os.sep+steamid, FOLDER_KEYS, steamid, dispname)

    final_links=[]
    final_mods=[]
    final_srvmods=[]
    for dispname, steamid in NEW_SRVMOD_LIST:
        san_dispname="@"+dispname
        final_links.append([WORKSHOP_DIR+os.sep+steamid, FOLDER_SERVERMODS+os.sep+san_dispname])
        final_srvmods.append("servermods/"+san_dispname)

    for dispname, steamid in NEW_MOD_LIST:
        san_dispname="@"+dispname
        final_links.append([WORKSHOP_DIR+os.sep+steamid, FOLDER_MODS+os.sep+san_dispname])
        final_mods.append("mods/"+san_dispname)

    for dispname, steamid in NEW_MAPS_LIST:
        san_dispname="@"+dispname
        final_links.append([WORKSHOP_DIR+os.sep+steamid, FOLDER_MODS+os.sep+san_dispname])
        final_mods.append("mods/"+san_dispname)

    logdebug("linking {}".format(final_links))
    for item_from, item_to in final_links:
        link_it(item_from, item_to, silent=True)

    return result,final_srvmods,final_mods



print("\n\nHALLO WELT, HALLO DON!\n", flush=True)
debug_skip_install=False
    
lognotice("\npreparing server...")

# remove folder and links and prepare new ones
startup_folder_clean_prepare()

if not parse_json_config():
    logerror("failed to handle json config file, terminating")
    exit(1)

# link mods, servermods and maps to the workshop items
result, server_mods, mods=link_external_share_with_workshop()
if not result:
    logerror("workshop item interlink failed")
    exit(1)

# add the server itself
lognotice("\ninstall / update arma server binary...")
    
if os.environ["SKIP_INSTALL"] in ["", "false"] and debug_skip_install==False:
    # Install Arma

    steamcmd = ["/steamcmd/steamcmd.sh"]
    steamcmd.extend(["+force_install_dir", "/arma3"])
    steamcmd.extend(["+login", os.environ["STEAM_USER"], os.environ["STEAM_PASSWORD"]])
    steamcmd.extend(["+app_update", "233780"])
    if env_defined("STEAM_BRANCH"):
        steamcmd.extend(["-beta", os.environ["STEAM_BRANCH"]])
    if env_defined("STEAM_BRANCH_PASSWORD"):
        steamcmd.extend(["-betapassword", os.environ["STEAM_BRANCH_PASSWORD"]])
    steamcmd.extend(["validate"])
    steamcmd.extend(["+quit"])
    subprocess.call(steamcmd)

# Mods

launch = "{} -filePatching -limitFPS={} -world={} {} {}".format(
    os.environ["ARMA_BINARY"],
    os.environ["ARMA_LIMITFPS"],
    os.environ["ARMA_WORLD"],
    os.environ["ARMA_PARAMS"],
    mod_param("mod", mods)
)

if os.environ["ARMA_CDLC"] != "":
    for cdlc in os.environ["ARMA_CDLC"].split(";"):
        launch += " -mod={}".format(cdlc)



clients = int(os.environ["HEADLESS_CLIENTS"])
if clients > 0:
    lognotice("\nstarting {} headless clients...".format(clients))

if clients != 0:
    with open(CONFIG_FILE) as config:
        data = config.read()
        regex = r"(.+?)(?:\s+)?=(?:\s+)?(.+?)(?:$|\/|;)"

        config_values = {}

        matches = re.finditer(regex, data, re.MULTILINE)
        for matchNum, match in enumerate(matches, start=1):
            config_values[match.group(1).lower()] = match.group(2)

        if "headlessclients[]" not in config_values:
            data += '\nheadlessclients[] = {"127.0.0.1"};\n'
        if "localclient[]" not in config_values:
            data += '\nlocalclient[] = {"127.0.0.1"};\n'

        with open("/tmp/arma3.cfg", "w") as tmp_config:
            tmp_config.write(data)
        launch += ' -config="/tmp/arma3.cfg"'

    client_launch = launch
    client_launch += " -client -connect=127.0.0.1 -port={}".format(os.environ["PORT"])
    if "password" in config_values:
        client_launch += " -password={}".format(config_values["password"])

    for i in range(0, clients):
        hc_template = Template(
            os.environ["HEADLESS_CLIENTS_PROFILE"]
        )  # eg. '$profile-hc-$i'
        hc_name = hc_template.substitute(
            profile=os.environ["ARMA_PROFILE"], i=i, ii=i + 1
        )

        hc_launch = client_launch + ' -name="{}"'.format(hc_name)
        print("LAUNCHING ARMA CLIENT {} WITH".format(i), hc_launch)
        subprocess.Popen(hc_launch, shell=True)

else:
    launch += ' -config="{}"'.format(CONFIG_FILE)

#lognotice("sleeping!")
#while(True):
#    time.sleep(1)
    
lognotice("\nstarting arma dedicated server...")


launch += ' -port={} -name="{}" -profiles="/arma3/config/profiles"'.format(
    os.environ["PORT"], os.environ["ARMA_PROFILE"]
)
if os.path.exists(SERVER_BASE):
    launch += ' -cfg="{}"'.format(SERVER_BASE)
if os.path.exists(PARAM_FILE):
    with open(PARAM_FILE) as f:
        cfg_param=f.readline()
        launch += ' {} '.format(cfg_param)

if len(server_mods):
    launch += mod_param("serverMod", server_mods)

print("LAUNCHING ARMA SERVER WITH", launch, flush=True)

os.system(launch)
