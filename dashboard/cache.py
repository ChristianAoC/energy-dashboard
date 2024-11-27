### CURRENTLY NOT IN USE

import requests
import uuid
import json
import os.path
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

load_dotenv()
apiBase = os.getenv("API_BASE")

deviceCacheTime = 7 # number of days when if smaller update cache
path = {
    "summary": "static/data/cache_summary/",
    "meter_obs": "static/data/cache_obs/",
    "meter": "static/data/cache_device/",
    "meter_ping": "static/data/cache_device/"
}

def getData (endpoint, args):
    # for summary (only endpoint for now): if filename exists, get that
    checkFile = path[endpoint] + args["from_time"] + "_" + args["to_time"] + ".json"
    if os.path.isfile(checkFile):
        with open(checkFile, 'r') as openfile:
            try:
                summary = json.load(openfile)
                return summary
            except:
                return "Found cache but JSON failed for: "+checkFile
        
    # get the data from the API, test if it's JSON
    try:
        r = requests.get(apiBase + endpoint, params=args)
        try:
            rjson = r.json()

            # filename to be from-to (summary)
            if "to_time" not in args:
                args["to_time"] = datetime.now().strftime("%Y-%m-%d")
            if "from_time" not in args:
                args["from_time"] = (datetime.strptime(args["to_time"], "%Y-%m-%d") - timedelta(days=7)).strftime("%Y-%m-%d")
            filename = path[endpoint] + args["from_time"] + "_" + args["to_time"] + ".json"
            
            # check for summary/devices to only write if the data is non-empty
            if len(rjson) < 50:
                return "API returned unusually few buildings. Abort."

            # open file (with random name so there's no clash, rename once done writing)
            tempFileName = str(uuid.uuid4())
            tempfile = os.path.join(os.path.dirname(filename), tempFileName)
            try:
                outfile = open(tempfile, 'w')
                try:
                    json.dump(rjson, outfile, indent=4)
                    outfile.close()
                    try:
                        os.replace(tempfile, filename)
                    except:
                        return "Renaming cache file failed"
                except:
                    return "JSON dump to file failed"
            except:
                return "Couldn't open temp cache file for writing"
        except:
            try:
                res = r.text
                return res
            except:
                return "Couldn't convert to JSON"
    except:
        return "API down or wrong query parameters"
