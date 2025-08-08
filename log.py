import datetime as dt

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

def create_log(msg: str, level: str, extra_info: str|None = None):
    # Import here to stop circular import issue
    from constants import log_level
    
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