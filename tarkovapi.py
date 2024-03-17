import requests
from datetime import datetime

playersearch = "https://player.tarkov.dev/name/"
playerendpoint = "https://player.tarkov.dev/account/"
graphendpoint = "https://api.tarkov.dev/graphql"
headers = {"Content-Type": "application/json"}
LEVELS = None
CONTAINERS = {
    "5783c43d2459774bbe137486",
    "590c60fc86f77412b13fddcf",
    "59fafd4b86f7745ca07e1232",
    "5c093e3486f77430cb02e593",
    "5d235bb686f77443f4331278",
    "60b0f6c058e0b0481a09ad11",
    "619cbf7d23893217ec30b689",
    "619cbf9e0a7c3a1a2731940a",
    "62a09d3bcf4a99369e262447"
}

def getItems(items):
    q = '{items( ids: ["%s"] ) { id shortName avg24hPrice }}' % '", "'.join(items)
    r = None
    response = requests.post(graphendpoint, headers=headers, json={'query': q})
    if response.status_code == 200:
        r = response.json()
    else:
        raise Exception("Query failed to run by returning code of {}. {}".format(response.status_code, q))
    return r['data']['items']


def convertDate(timestamp, fmat='%m/%d/%y %H:%M'):
    return datetime.utcfromtimestamp(timestamp).strftime(fmat)

def getLevelData():
    global LEVELS
    if not LEVELS:
        r = None
        response = requests.post(graphendpoint, headers=headers, json={'query': "{ playerLevels {level exp} }"})
        if response.status_code == 200:
            r = response.json()
        else:
            raise Exception("Query failed to run by returning code of {}.".format(response.status_code))
        LEVELS = r['data']['playerLevels']
    return LEVELS

def convertExp2Level(exp):
    lvldata = getLevelData()
    out = 0
    for l in lvldata:
        if exp >= l['exp']:
            out = l['level']
        else:
           return out

def searchPlayer(name):
    response = requests.get(playersearch+str(name), headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception("Player Search failed {}. {}".format(response.status_code, query))


def openButt(inv):
    buttid = None
    buttitems = {}
    containers = []
    # get buttid
    for item in inv:
        if "slotId" in item:
            if item['slotId'] == "SecuredContainer":
                buttid = item['_id']
                break
    # get buttitems
    for item in inv:
        if "parentId" in item and item["parentId"] == buttid:
            count = 1
            iid = item["_tpl"]
            buttitems[iid] = {}
            if "upd" in item:
                count = item["upd"].get("StackObjectsCount", 1)
            if iid in CONTAINERS: #check if container
                containers.append(item["_id"])
            buttitems[iid]['count'] = count
    # get items in containers
    for item in inv:
        if "parentId" in item and item["parentId"] in containers:
            count = 1
            iid = item["_tpl"]
            buttitems[iid] = {}
            if "upd" in item:
                count = item["upd"].get("StackObjectsCount", 1)
            buttitems[iid]['count'] = count
    # get names and prices
    buttcontents = getItems(list(buttitems.keys()))
    for item in buttcontents:
        buttitems[item['id']]['price'] = item['avg24hPrice'] * buttitems[item['id']]['count']
        buttitems[item['id']]['name'] = item['shortName']
    return buttitems


def getPlayer(player):
    response = requests.get(playerendpoint+str(player['aid']), headers=headers)
    r = None
    if response.status_code == 200:
        r = response.json()
    else:
        raise Exception("Player Get failed {}. {}".format(response.status_code, query))
    pinfo = r["info"]
    pmc = r["pmcStats"]["eft"]
    scav = r["scavStats"]["eft"]
    e = r['equipment']
    #
    butt = openButt(e["Items"])
    buttvalue = 0
    for i in butt:
        buttvalue += int(butt[i]['price'])
    #
    pmcStats = {}
    for item in pmc['overAllCounters']['Items']:
        if item['Key'][0] == "Sessions":
            pmcStats['raids'] = item['Value']
        elif item['Key'][0] == "Kills":
            pmcStats['kills'] = item['Value']
        elif item['Key'][0] == "Deaths":
            pmcStats['deaths'] = item['Value']
    pmcStats['kd'] = round(pmcStats['kills']/pmcStats['deaths'], 2)
    pmcStats['kpr'] = round(pmcStats['kills']/pmcStats['raids'], 2)
    scavStats = {}
    for item in scav['overAllCounters']['Items']:
        if item['Key'][0] == "Sessions":
            scavStats['raids'] = item['Value']
        elif item['Key'][0] == "Kills":
            scavStats['kills'] = item['Value']
        elif item['Key'][0] == "Deaths":
            scavStats['deaths'] = item['Value']
    scavStats['kd'] = round(scavStats['kills']/scavStats['deaths'], 2)
    scavStats['kpr'] = round(scavStats['kills']/scavStats['raids'], 2)
    #
    return {
        "name": pinfo['nickname'],
        "banned": pinfo['bannedState'],
        "exp": pinfo['experience'],
        "level": convertExp2Level(int(pinfo['experience'])),
        "regDate": convertDate(pinfo['registrationDate']),
        "timePlayed": str(round(pmc["totalInGameTime"]/3600, 2))+"hrs",
        "totalRaids": pmcStats['raids'] + scavStats['raids'],
        "totalKills": pmcStats['kills'] + scavStats['kills'],
        "totalDeaths": pmcStats['deaths'] + scavStats['deaths'],
        "totalKD": round(int(pmcStats['kills'] + scavStats['kills']) / int(pmcStats['deaths'] + scavStats['deaths']), 2),
        "expHr": round(pinfo['experience'] / int(pmc["totalInGameTime"]/3600), 2),
        "killsHr": round(int(pmcStats['kills'] + scavStats['kills']) / int(pmc["totalInGameTime"]/3600), 2),
        "raidsHr": round(int(pmcStats['raids'] + scavStats['raids']) / int(pmc["totalInGameTime"]/3600), 2),
        "killsRaid": round(int(pmcStats['kills'] + scavStats['kills']) / int(pmcStats['raids'] + scavStats['raids']), 2),
        #"pmc": pmcStats,
        #"scav": scavStats,
        "butthole": butt,
        "buttValue": buttvalue
    }

if __name__ == '__main__':
    import sys
    from pprint import pprint
    if len(sys.argv) > 1:
        p = getPlayer(searchPlayer(str(sys.argv[1]))[0])
        pprint(p)
    else:
        print("missing arg")