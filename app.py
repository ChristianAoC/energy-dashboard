from flask import Flask
from api.api import api_bp
from dashboard.main import dashboard_bp
import os
from dotenv import load_dotenv

app = Flask(__name__)
app.register_blueprint(api_bp, url_prefix='/api')
app.register_blueprint(dashboard_bp)

load_dotenv()
app.config["SITE_NAME"] = os.getenv("SITE_NAME") or "Energy Dashboard"
app.config["MAZEMAP_CAMPUS_ID"] = os.getenv("MAZEMAP_CAMPUS_ID") or 121
app.config["MAZEMAP_LNG"] = os.getenv("MAZEMAP_LNG") or "13.270286316716465"
app.config["MAZEMAP_LAT"] = os.getenv("MAZEMAP_LAT") or "52.502217640505705"
app.config["IFRAME_CAPAVIS"] = os.getenv("IFRAME_CAPAVIS")
app.config["IFRAME_ENERGY_USAGE"] = os.getenv("IFRAME_ENERGY_USAGE")
app.config["DEFAULT_USER_LEVEL"] = os.getenv("DEFAULT_USER_LEVEL") or 5
app.config["USER_LEVEL_VIEW_DASHBOARD"] = os.getenv("USER_LEVEL_VIEW_DASHBOARD") or 5
app.config["USER_LEVEL_VIEW_COMMENTS"] = os.getenv("USER_LEVEL_VIEW_COMMENTS") or 5
app.config["USER_LEVEL_SUBMIT_COMMENTS"] = os.getenv("USER_LEVEL_SUBMIT_COMMENTS") or 25
app.config["USER_LEVEL_EDIT_COMMENTS"] = os.getenv("USER_LEVEL_EDIT_COMMENTS") or 35
app.config["USER_LEVEL_ADMIN"] = os.getenv("USER_LEVEL_ADMIN") or 99

app.secret_key = os.getenv("SECRET_KEY")
if app.secret_key == None:
    print("Secret key missing!!! Make sure you set a secret key in the .env file before continuing.")
