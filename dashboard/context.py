import json
import os
import uuid
from datetime import datetime

filename = "context.json"

def add_context(contextElem):
    if not os.path.isfile(filename):
        f = open(filename, "w")
        f.close()
    with open(filename, 'r') as openfile:
        context = json.load(openfile)
        max_id = 0
        for item in context:
            try:
                this_id = int(item["id"])
                if this_id > max_id:
                    max_id = this_id
            except ValueError:
                print("ID wasn't a number.")
        contextElem["id"] = max_id + 1
        context.append(contextElem)
    tempfile = os.path.join(os.path.dirname(filename), str(uuid.uuid4()))
    with open(tempfile, 'w') as outfile:
        json.dump(context, outfile, indent=4)
    os.replace(tempfile, filename)
    # always returns success... but guess that's ok? for now?
    return "success"

def edit_context(contextElem):
    if not os.path.isfile(filename):
        return "Context file missing"
    with open(filename, 'r') as openfile:
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
    with open(filename, 'r') as openfile:
        context = json.load(openfile)
        for i in range(len(context)):
            if context[i]["id"] == int(contextID):
                context.pop(i)
                break
    tempfile = os.path.join(os.path.dirname(filename), str(uuid.uuid4()))
    with open(tempfile, 'w') as outfile:
        json.dump(context, outfile, indent=4)
    os.replace(tempfile, filename)
    return "success"

def get_context(args):
    if not os.path.isfile(filename):
        return "Context file missing"
    with open(filename, 'r') as openfile:
        context = json.load(openfile)
        timeFormat = "%Y-%m-%d %H:%M"
        for key, value in args.items():
            if key == "sensor":
                if value == "all":
                    continue
                else:
                    sensors = args["sensor"].split(";")
            result = []
            for i in range(len(context)):
                if key in context[i]:
                    if key == "id" or key == "author":
                        if context[i][key].casefold() == value.casefold():
                            result.append(context[i])
                    if key == "type":
                        # once recurring events are processed:
                        # leave the recurring events in and add a recurring lookup table
                        #if context[i][key] == "Recurring" or context[i][key].casefold() == value.casefold():
                        if context[i][key].casefold() == value.casefold():
                            result.append(context[i])
                    if key == "sensor":
                        if context[i][key] in sensors:
                            result.append(context[i])
                    # add fuzzy logic... not sure what/how
                    if key == "start":
                        try:
                            if datetime.strptime(context[i]["end"], timeFormat) > datetime.strptime(value, timeFormat):
                                result.append(context[i])
                        except ValueError as e:
                            print(f"Error: {e}")
                    if (key == "end"):
                        try:
                            if datetime.strptime(context[i]["start"], timeFormat) < datetime.strptime(value, timeFormat):
                                result.append(context[i])
                        except ValueError as e:
                            print(f"Error: {e}")
            context = result
    return result

def view_all():
    if not os.path.isfile(filename):
        return "Context file missing"
    with open(filename, 'r') as openfile:
        context = json.load(openfile)
        return context
