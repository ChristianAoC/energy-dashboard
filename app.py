import os
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)
import sys
sys.path.append(dname)

from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
import base64
from datetime import timezone
from dotenv import load_dotenv
import requests

from api.endpoints.context import context_api_bp
from api.endpoints.data import data_api_bp
from api.endpoints.settings import settings_api_bp
from api.endpoints.user import users_api_bp
import constants
from dashboard.main import dashboard_bp
import database
import log
import models
from settings import load_settings, default_settings
import shutdown


app = Flask(__name__)
successful_initialisation = database.init(app)
# needed because sometimes WSGI is a bit thick
application = app

###########################################################
###              Check required files exist             ###
###########################################################

# This is so that the log can be written to if an error occurs when loading constants
with app.app_context():
    # Need to get offline mode manually from database as g.settings hasn't been created as this isn't a request
    result = database.db.session.execute(
        database.db.Select(models.Settings)
        .where(models.Settings.category == "data")
        .where(models.Settings.key == "offline_mode")
    ).scalar_one_or_none()
    offline_mode = True
    if result is not None:
        offline_mode = result.value
    app.config["offline_mode"] = offline_mode
    
    if offline_mode and not os.path.exists(os.path.join(constants.DATA_DIR, "offline")):
        print("\n" + "="*20)
        print("\tERROR: You are running in offline mode without any offline data!")
        print("\tPlease place your data in ./data/offline/")
        print("="*20 + "\n")
        log.write(msg="You are running in offline mode without any offline data",
                extra_info="Place your data in ./data/offline/",
                level=log.critical)
        successful_initialisation = False

# Show all error messages before exiting
if not successful_initialisation:
    shutdown.hard()
del successful_initialisation

###########################################################
###                      Blueprints                     ###
###########################################################

@app.before_request
def call_load_settings():
    load_settings()

app.register_blueprint(data_api_bp, url_prefix='/api')
app.register_blueprint(context_api_bp, url_prefix='/api/context')
app.register_blueprint(users_api_bp, url_prefix='/api/user')
app.register_blueprint(settings_api_bp, url_prefix='/api/settings')
app.register_blueprint(dashboard_bp)

load_dotenv()
app.secret_key = os.getenv("SECRET_KEY") or os.urandom(24)
app.config["internal_api_key"] = base64.urlsafe_b64encode(os.urandom(96)).decode().rstrip('=')

###########################################################
###               Set up scheduled tasks                ###
###########################################################

def run_scheduled_requests(url: str, method: str|None = None, headers: dict|None = None, params: dict|None = None, send_data: dict|None = None):
    if method is None:
        method = "get"
    if headers is None:
        headers = {}
    if params is None:
        params = {}
    if send_data is None:
        send_data = {}

    request_response = requests.request(method=method, url=url, headers=headers, data=send_data, params=params)
    
    if request_response.status_code != 200:
        print("\n" + "="*20)
        print(f"\tERROR: Scheduled api call to {url} failed with code {request_response.status_code}!")
        print("\tPlease manually call the endpoint to complete the scheduled task")
        print("="*20 + "\n")
        log.write(msg=f"Scheduled api call to {url} failed with code {request_response.status_code}",
                       level=log.error)
    else:
        print(f"Finished scheduled request to: {url}")
        log.write(msg=f"Finished scheduled request to: {url}", level=log.info)

# Need to get background task timing manually from database as g.settings hasn't been created as this isn't a request
with app.app_context():
    result = database.db.session.execute(
        database.db.Select(models.Settings)
        .where(models.Settings.category == "server")
        .where(models.Settings.key == "BACKGROUND_TASK_TIMING")
    ).scalar_one_or_none()
    val = default_settings["server"]["BACKGROUND_TASK_TIMING"]
    if result is not None:
        val = result.value
    background_task_timing = val.split(":")
    
    result = database.db.session.execute(
        database.db.Select(models.Settings)
        .where(models.Settings.category == "server")
        .where(models.Settings.key == "login_code_timeout")
    ).scalar_one_or_none()
    login_code_task_timing = default_settings["server"]["login_code_timeout"]
    if result is not None:
        login_code_task_timing = result.value

scheduler = BackgroundScheduler()
overnight_trigger = CronTrigger(
    hour = background_task_timing[0],
    minute = background_task_timing[1],
    timezone = timezone.utc,
    jitter = 60 # Jitter randomises the time the scheduled task runs by +-x to avoid sudden spikes in cpu usage
)
login_code_trigger = IntervalTrigger(
    minutes = login_code_task_timing,
    jitter = 60 # Jitter randomises the time the scheduled task runs by +-x to avoid sudden spikes in cpu usage
)

scheduler.add_job(run_scheduled_requests,
                  overnight_trigger,
                  id="meter_health_cache_generation",
                  args=("http://127.0.0.1:5000/api/regeneratecache", "get",
                        {"Authorization": app.config["internal_api_key"]}))
scheduler.add_job(run_scheduled_requests,
                  overnight_trigger,
                  id="usage_summary_cache_generation",
                  args=("http://127.0.0.1:5000/api/summary", "get", {"Authorization": app.config["internal_api_key"]}))
scheduler.add_job(run_scheduled_requests,
                  overnight_trigger,
                  id="clean_database_all",
                  args=("http://127.0.0.1:5000/api/settings/clean-database", "post",
                        {"Authorization": app.config["internal_api_key"]}))

scheduler.add_job(run_scheduled_requests,
                  overnight_trigger,
                  id="clean_database_login_codes",
                  args=("http://127.0.0.1:5000/api/settings/clean-database?type=login_codes","post",
                        {"Authorization": app.config["internal_api_key"]}))

scheduler.start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)