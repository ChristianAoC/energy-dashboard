import os
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)
import sys
sys.path.append(dname)

from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import base64
from datetime import timezone
from dotenv import load_dotenv
import requests

from api.api import api_bp
from dashboard.main import dashboard_bp
import database

app = Flask(__name__)
database.init(app)
# needed because sometimes WSGI is a bit thick
application = app

app.register_blueprint(api_bp, url_prefix='/api')
app.register_blueprint(dashboard_bp)

load_dotenv()
app.secret_key = os.getenv("SECRET_KEY") or os.urandom(24)

app.config["SITE_NAME"] = os.getenv("SITE_NAME") or "Energy Dashboard"
val = os.getenv("OFFLINE_MODE", "True")
app.config["OFFLINE_MODE"] = val.strip().lower() in ("1", "true", "yes", "on")

# this is the mazemap ID for Lancaster Campus university and its coordinates, by default
app.config["MAZEMAP_CAMPUS_ID"] = int(os.getenv("MAZEMAP_CAMPUS_ID", "341"))
app.config["MAZEMAP_LNG"] = os.getenv("MAZEMAP_LNG") or "-2.780372"
app.config["MAZEMAP_LAT"] = os.getenv("MAZEMAP_LAT") or "54.008809"

# data backend settings.
# those are kept in api.py for now, just keeping here to show which ones are available (and to move here later, possibly)
#val = os.getenv("OFFLINE_MODE", "True")
#app.config["OFFLINE_MODE"] = val.strip().lower() in ("1", "true", "yes", "on")
#app.config["INFLUX_URL"] = os.getenv("INFLUX_URL")
#app.config["INFLUX_PORT"] = os.getenv("INFLUX_PORT")
#app.config["INFLUX_USER"] = os.getenv("INFLUX_USER")
#app.config["INFLUX_PASS"] = os.getenv("INFLUX_PASS")
#app.config["HEALTH_CHECK_UPDATE_TIME"] = int(os.getenv("HEALTH_CHECK_UPDATE_TIME", "9"))

# STMP settings - required for users to create and activate accounts automatically
# if no server at hand, make a Google account and create an app password
app.config["SMTP_ADDRESS"] = os.getenv("SMTP_ADDRESS")
app.config["SMTP_PASSWORD"] = os.getenv("SMTP_PASSWORD")
app.config["SMTP_SERVER"] = os.getenv("SMTP_SERVER")
app.config["SMTP_PORT"] = os.getenv("SMTP_PORT")
val = os.getenv("SMTP_ENABLED", "False")
app.config["SMTP_ENABLED"] = val.strip().lower() in ("1", "true", "yes", "on")

# you can restrict email domains, and also create "demo email domains" which allow account creation without activation email.
app.config["REQUIRED_EMAIL_DOMAINS"] = os.getenv("REQUIRED_EMAIL_DOMAINS")
app.config["DEMO_EMAIL_DOMAINS"] = os.getenv("DEMO_EMAIL_DOMAINS")

# set appropriate user levels in .env (at the moment user levels can only be manually changed in users.json)
app.config["DEFAULT_USER_LEVEL"] = int(os.getenv("DEFAULT_USER_LEVEL", "3"))
app.config["USER_LEVEL_VIEW_DASHBOARD"] = int(os.getenv("USER_LEVEL_VIEW_DASHBOARD", "1"))
app.config["USER_LEVEL_VIEW_HEALTHCHECK"] = int(os.getenv("USER_LEVEL_VIEW_HEALTHCHECK", "1"))
app.config["USER_LEVEL_VIEW_COMMENTS"] = int(os.getenv("USER_LEVEL_VIEW_COMMENTS", "1"))
app.config["USER_LEVEL_SUBMIT_COMMENTS"] = int(os.getenv("USER_LEVEL_SUBMIT_COMMENTS", "3"))
app.config["USER_LEVEL_EDIT_COMMENTS"] = int(os.getenv("USER_LEVEL_EDIT_COMMENTS", "4"))
app.config["USER_LEVEL_ADMIN"] = int(os.getenv("USER_LEVEL_ADMIN", "5"))

app.config["internal_api_key"] = base64.urlsafe_b64encode(os.urandom(96)).decode().rstrip('=')

# #################################################################
def run_scheduled_requests(url: str, method: str = "get", headers: dict = {}, params: dict = {}, send_data: dict = {}):
    request_response = requests.request(method=method, url=url, headers=headers, data=send_data, params=params)
    
    if request_response.status_code != 200:
        print("\n" + "="*20)
        print(f"\tERROR: Scheduled api call to {url} failed with code {request_response.status_code}!")
        print("\tPlease manually call the endpoint to complete the scheduled task")
        print("="*20 + "\n")
    else:
        print(f"Finished scheduled request to: {url}")

val = os.getenv("BACKGROUND_TASK_TIMING", "02:00")
background_task_timing = val.split(":")

scheduler = BackgroundScheduler()
trigger = CronTrigger(
    hour = background_task_timing[0],
    minute = background_task_timing[1],
    timezone = timezone.utc,
    jitter = 60 # Jitter randomises the time the scheduled task runs by +-x to avoid sudden spikes in cpu usage
)

scheduler.add_job(run_scheduled_requests,
                  trigger,
                  id="meter_health_cache_generation",
                  args=("http://127.0.0.1:5000/api/regeneratecache", "get", {"Authorization": app.config["internal_api_key"]}))
scheduler.add_job(run_scheduled_requests,
                  trigger,
                  id="usage_summary_cache_generation",
                  args=("http://127.0.0.1:5000/api/summary", "get", {"Authorization": app.config["internal_api_key"]}))

scheduler.start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)