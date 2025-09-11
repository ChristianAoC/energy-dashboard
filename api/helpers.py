from flask import g, has_request_context

import datetime as dt


def calculate_time_args(from_time_requested: dt.datetime|str|None = None, to_time_requested: dt.datetime|str|None = None, date_range_requested: int|None = None, desired_time_range: int = 30) -> tuple[dt.datetime,dt.datetime,int]:
    time_range = date_range_requested if date_range_requested is not None else desired_time_range

    from_time: dt.datetime = None # type: ignore
    if type(from_time_requested) is dt.datetime:
        from_time = from_time_requested
    
    to_time: dt.datetime = None # type: ignore
    if type(to_time_requested) is dt.datetime:
        to_time = to_time_requested
    
    if type(from_time_requested) is str:
        from_time = dt.datetime.combine(dt.datetime.strptime(from_time_requested,"%Y-%m-%d"), dt.datetime.min.time(), tzinfo=dt.timezone.utc)
    if type(to_time_requested) is str:
        to_time = dt.datetime.combine(dt.datetime.strptime(to_time_requested, "%Y-%m-%d"), dt.datetime.max.time(), tzinfo=dt.timezone.utc)
    
    if not g.settings["offline_mode"]:
        if to_time_requested is None:
            to_time = dt.datetime.combine(dt.date.today(), dt.datetime.max.time(), tzinfo=dt.timezone.utc)

        if from_time_requested is None:
            from_time = to_time - dt.timedelta(days=time_range, seconds=1)
    else:
        offline_to_time_raw = g.settings["offline_data_end_time"]
        offline_from_time_raw = g.settings["offline_data_start_time"]
        
        offline_to_time = dt.datetime.strptime(offline_to_time_raw, "%Y-%m-%dT%H:%M:%S%z")
        offline_from_time = dt.datetime.strptime(offline_from_time_raw, "%Y-%m-%dT%H:%M:%S%z")
        
        changed_time = False
        if to_time is not None:
            # Need to make sure that the provided data is within the offline data
            if to_time > offline_to_time or to_time < offline_from_time:
                to_time = offline_to_time
                changed_time = True
        else:
            to_time = offline_to_time
            changed_time = True
        
        if from_time is not None:
            # Need to make sure that the provided data is within the offline data
            if from_time > offline_to_time or from_time < offline_from_time:
                from_time = offline_from_time
                changed_time = True
            
            if from_time > to_time:
                from_time = offline_from_time
                changed_time = True
        else:
            from_time = offline_from_time
            changed_time = True

        if changed_time or (from_time - to_time) > dt.timedelta(days=time_range):
            from_time = to_time - dt.timedelta(days=time_range)
    
    days = (to_time.date() - from_time.date()).days

    return from_time, to_time, days

## Cleans the provided file name by replacing / with _
## file_name - The file name to be cleaned
def clean_file_name(file_name: str):
    file_name = file_name.replace("/", "_")
    file_name = file_name.replace("\\", "_")
    file_name = file_name.replace(" ", "_")
    file_name = file_name.replace("?", "_")
    file_name = file_name.replace(",", "_")
    return file_name

# Uses a whitelist for which keys are allowed to be returned to the user to help stop leaking data
def data_cleaner(data: list[dict]|dict, keys: list) -> list[dict]|dict:
    if keys is None or keys == {}:
        return data
    
    if type(data) == dict:
        return {key: data.get(key) for key in keys}
    
    out = []
    for data_point in data:
        out.append({key: data_point.get(key) for key in keys})
    
    return out

def has_g_support():
    try:
        return has_request_context()
    except RuntimeError:
        return False