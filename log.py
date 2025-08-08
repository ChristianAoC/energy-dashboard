import datetime as dt

import models
from database import db

info = "info"
warning = "warning"
error = "error"
critical = "critical"

index = {
    "info": 1,
    "warning": 2,
    "error": 3,
    "critical": 4
}

def create_log(msg: str, level: str):
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
            level=level
        )
        db.session.add(new_log)
        db.session.commit()
    except:
        db.session.rollback()