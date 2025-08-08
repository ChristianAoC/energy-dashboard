import datetime as dt
from sqlalchemy import or_

from constants import log_level
from database import db
import models


# Levels were loosly based on https://stackoverflow.com/a/2031209 (and other anwers for that question),
# along with past experience.

# Any general useful information, e.g:
# - starting/finishing an operation
# - processing times
# - bypassing authentication (in a normal case)
# - skipping something (a meter/building in a health check / summary)
# Useful for debugging and must not require direct intervention, it should be safe to ignore/disgard
info = "info"

# An error that doesn't stop the operation from continuing, e.g:
# - an error while reading an individual record from a json/csv/xlsx file
# - an error while reading a cache, but we can just recalculate the information
# - an error saving a cache but we can still return the information
# - an external call is sent to a user level protected endpoint without being logged it
# May require direct intervention from an administrator
warning = "warning"

# An error that stops the operation from continuing *but not the service as a whole*, e.g:
# - an internal api call fails
# - unable to locate offline data
# - an error occurs generating cache that cannot be recovered from
# Should require direct intervention from an administrator
# Note: These logs should contain both a message and extra info
error = "error"

# An error that stops the service from running/starting, e.g:
# - a required file is missing
# - can't access a 
# Requires direct, immediate intervention from an adminitrator
# Note: These logs must contain both a message and extra info
critical = "critical"

index = {
    "info": 1,
    "warning": 2,
    "error": 3,
    "critical": 4
}

def write(msg: str, level: str, extra_info: str|None = None):
    level_index = index.get(level.lower(), 1)
    minimum_index = index.get(log_level.lower(), 1)
    
    if level_index < minimum_index:
        return
    
    try:
        new_log = models.Log(
            timestamp=dt.datetime.now(),
            message=msg,
            level=level,
            info=extra_info
        )
        db.session.add(new_log)
        db.session.commit()
    except:
        db.session.rollback()

def read(from_time: dt.datetime|None = None, to_time: dt.datetime|None = None, minimum_level: str|None = None,
         exact_level: str|None = None, count: int|None = None, newest_first: bool = True) -> list|None:
    if exact_level in index.keys():
        minimum_level = None
    else:
        exact_level = None
    
    if minimum_level not in index.keys():
        minimum_level = None
    
    statement = db.Select(models.Log)
    if from_time is not None:
        statement = statement.where(models.Log.timestamp >= from_time)
    
    if to_time is not None:
        statement = statement.where(models.Log.timestamp <= to_time)
    
    if exact_level is not None:
        statement = statement.where(models.Log.level == exact_level)
    elif minimum_level is not None:
        if minimum_level == info:
            statement = statement.where(or_(models.Log.level == info, models.Log.level == warning, # type: ignore
                                            models.Log.level == error, models.Log.level == critical)) # type: ignore
        elif minimum_level == warning:
            statement = statement.where(or_(models.Log.level == warning, models.Log.level == error, # type: ignore
                                            models.Log.level == critical)) # type: ignore
        elif minimum_level == error:
            statement = statement.where(or_(models.Log.level == error, models.Log.level == critical)) # type: ignore
        elif minimum_level == critical:
            statement = statement.where(models.Log.level == critical)
    
    if newest_first:
        statement = statement.order_by(models.Log.timestamp.desc()) # type: ignore
    else:
        statement = statement.order_by(models.Log.timestamp.asc()) # type: ignore 
    return [x.to_dict() for x in db.session.execute(statement).scalars().fetchmany(count)]