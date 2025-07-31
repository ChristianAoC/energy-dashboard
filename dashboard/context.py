import json
import os
import uuid
from datetime import datetime

filename = "data/context.json"

def add_context(contextElem):
    if not os.path.isfile(filename) or os.path.getsize(filename) == 0:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump([], f)
    os.chmod(filename, 0o777)

    with open(filename, 'r', encoding="utf-8", errors="replace") as openfile:
        context = json.load(openfile)

    max_id = 0
    for item in context:
        try:
            this_id = int(item["id"])
            if this_id > max_id:
                max_id = this_id
        except (ValueError, KeyError):
            print("ID wasn't a number or missing.")

    contextElem["id"] = max_id + 1
    context.append(contextElem)

    tempfile = os.path.join(os.path.dirname(filename), str(uuid.uuid4()))
    with open(tempfile, 'w', encoding="utf-8") as outfile:
        json.dump(context, outfile, indent=4)
    os.replace(tempfile, filename)
    return "success"

def edit_context(contextElem):
    if not os.path.isfile(filename):
        return "Context file missing"
    with open(filename, 'r', encoding="utf-8", errors="replace") as openfile:
        context = json.load(openfile)
        for i in range(len(context)):
            if int(context[i]["id"]) == int(contextElem["id"]):
                context[i] = contextElem
                break
    tempfile = os.path.join(os.path.dirname(filename), str(uuid.uuid4()))
    with open(tempfile, 'w') as outfile:
        json.dump(context, outfile, indent=4)
    os.replace(tempfile, filename)
    return "success"

def delete_context(contextID):
    if not os.path.isfile(filename):
        return "Context file missing"
    with open(filename, 'r', encoding="utf-8", errors="replace") as openfile:
        context = json.load(openfile)
        for i in range(len(context)):
            if int(context[i]["id"]) == int(contextID):
                # don't delete, just set delete flag
                #context.pop(i)
                context[i]["deleted"] = 1
                break
    tempfile = os.path.join(os.path.dirname(filename), str(uuid.uuid4()))
    with open(tempfile, 'w') as outfile:
        json.dump(context, outfile, indent=4)
    os.replace(tempfile, filename)
    return "success"

def get_context(args):
    if not os.path.isfile(filename):
        return []

    with open(filename, 'r', encoding="utf-8", errors="replace") as openfile:
        context = json.load(openfile)

    # Parameters
    meters = args.get("meter", "").split(",")
    start_str = args.get("start")
    end_str = args.get("end")

    # Parse times
    timeFormat = "%Y-%m-%d %H:%M"
    try:
        start_dt = datetime.strptime(start_str, timeFormat) if start_str else None
        end_dt = datetime.strptime(end_str, timeFormat) if end_str else None
    except ValueError:
        return []

    filtered = []

    for entry in context:
        entry_meter = entry.get("meter")
        entry_start = datetime.strptime(entry["start"], timeFormat)
        entry_end = datetime.strptime(entry["end"], timeFormat)

        # 1. Meter match
        if meters and entry_meter not in meters:
            continue

        # 2. Time overlap check
        if start_dt and end_dt:
            if entry_end < start_dt or entry_start > end_dt:
                continue

        filtered.append(entry)

    return filtered

def view_all():
    if not os.path.isfile(filename):
        return "Context file missing"
    with open(filename, 'r', encoding="utf-8", errors="replace") as openfile:
        context = json.load(openfile)
        for i, c in enumerate(context):
            if "deleted" in c:
                if c["deleted"] == 1 or c["deleted"] == "1":
                    context.pop(i)
        return context
