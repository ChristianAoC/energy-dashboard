import os
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)
import sys
sys.path.append(dname)

from flask import Flask, g, request
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import base64
from datetime import timezone
from dotenv import load_dotenv
import requests

from api.endpoints.context import context_api_bp
from api.endpoints.data import data_api_bp
from api.endpoints.settings import settings_api_bp
from api.endpoints.user import users_api_bp
from api.settings import load_settings, default_settings
import constants
from dashboard.main import dashboard_bp
import database
import log
import models


app = Flask(__name__)
database.init(app)
# needed because sometimes WSGI is a bit thick
application = app

###########################################################
###              Check required files exist             ###
###########################################################
# This is so that the log can be written to if an error occurs when loading constants

cannot_initialise = False

with app.app_context():
    # Need to get offline mode manually from database as g.settigns hasn't been created as this isn't a request
    result = database.db.session.execute(
        database.db.Select(models.Settings)
        .where(models.Settings.key == "offline_mode")
    ).scalar_one_or_none()
    offline_mode = True
    if result is not None:
        offline_mode = result.value
    app.config["offline_mode"] = offline_mode
    
    if offline_mode and not os.path.exists(os.path.join(constants.DATA_DIR, "offline")):
        print("\n" + "="*20)
        print("\tERROR: You are runnning in offline mode without any offline data!")
        print("\tPlease place your data in ./data/offline/")
        print("="*20 + "\n")
        log.write(msg="You are runnning in offline mode without any offline data",
                extra_info="Place your data in ./data/offline/",
                level=log.critical)
        cannot_initialise = True

    if offline_mode and not os.path.exists(constants.offline_meta_file):
        result = constants.generate_offine_meta()
        if not result:
            print("\n" + "="*20)
            print("\tERROR: You are runnning in offline mode with no offline metadata (and it couldn't be generated)!")
            print("\tPlease place your metadata in ./data/meta/offline_data.json")
            print("="*20 + "\n")
            log.write(msg="You are runnning in offline mode with no offline metadata (and it couldn't be generated)",
                    extra_info="Place your metadata in ./data/meta/offline_data.json",
                    level=log.critical)
            cannot_initialise = True

    if not os.path.exists(constants.benchmark_data_file):
        print("\n" + "="*20)
        print("\tERROR: You have removed the included benchmark data!")
        print("\tPlease place the benchmark data in ./data/benchmarks.json")
        print("="*20 + "\n")
        log.write(msg="Can't find benchmark data",
                extra_info="Place the benchmark data in ./data/benchmarks.json, an example is included in the repo",
                level=log.critical)
        cannot_initialise = True

    if not os.path.exists(constants.mazemap_polygons_file):
        print("\n" + "="*20)
        print("\tERROR: You don't have any mazemap polygons defined!")
        print("\tPlease place the data in ./data/mazemap_polygons.json")
        print("="*20 + "\n")
        log.write(msg="Can't find any mazemap polygons",
                extra_info="Place the polygon data in ./data/mazemap_polygons.json",
                level=log.critical)
        cannot_initialise = True

# Show all error messages before exiting
if cannot_initialise:
    sys.exit(1)
del cannot_initialise

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

def run_scheduled_requests(url: str, method: str = "get", headers: dict = {}, params: dict = {}, send_data: dict = {}):
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

# Need to get backgound task timing manually from database as g.settigns hasn't been created as this isn't a request
with app.app_context():
    result = database.db.session.execute(
        database.db.Select(models.Settings)
        .where(models.Settings.key == "BACKGROUND_TASK_TIMING")
    ).scalar_one_or_none()
    val = default_settings["BACKGROUND_TASK_TIMING"]
    if result is not None:
        val = result.value
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