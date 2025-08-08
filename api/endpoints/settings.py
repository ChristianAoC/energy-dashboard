from flask import Blueprint, make_response, request, jsonify

import api.endpoints.data as data_api_bp
from database import db
import models


settings_api_bp = Blueprint('metadata_api_bp', __name__, static_url_path='')

def create_record(key: str, value):
    try:
        new_record = models.Settings(
            key=key,
            value=value,
        )
        db.session.add(new_record)
        db.session.commit()
    except:
        db.session.rollback()
        raise ValueError

def update_record(obj: models.Settings, value):
    try:
        obj.value = value
        db.session.commit()
    except:
        db.session.rollback()

## Returns the data stored with the given key (or all records as a dict if no key is sent)
##
## Parameters:
## key - The key to search for, if not given we return all key-value pairs in a dict
##
## Example:
## http://127.0.0.1:5000/api/settings/
## http://127.0.0.1:5000/api/settings/?key=key
@settings_api_bp.route("/", methods=["GET"])
@data_api_bp.required_user_level("USER_LEVEL_ADMIN")
def get():
    statement = db.select(models.Settings)
    try:
        key = request.args["key"]
    except:
        key = None
    
    if key is None:
        result = db.session.execute(statement).scalars().all()
        out = {}
        for entry in result:
            out[entry.key] = entry.value
        return make_response(jsonify(out), 200)
    
    statement = statement.where(models.Settings.key == key)
    result = db.session.execute(statement).scalar_one_or_none()
    if result is None:
        return make_response("Key not found", 404)
    return make_response(jsonify(result.value), 200)

## Creates/updates settings records 
##
## Send the data in the following format:
## json = {"key": "value"}
##
## Example request (python requests format):
## requests.post("http://127.0.0.1:5000/api/settings/",
##               headers = {'Content-type': 'application/json'},
##               json={
##                   "str": "test",
##                   "int": 1,
##                   "float": 2.3,
##                   "bool": True,
##                   "dict": {"test": "me", "out": "!"}
##                   }
##              )
##
## Example:
## http://127.0.0.1:5000/api/settings/
@settings_api_bp.route("/", methods=["POST"])
@data_api_bp.required_user_level("USER_LEVEL_ADMIN")
def post():
    if request.content_type != "application/json":
        return make_response("Invalid data", 400)
    
    try:
        data = request.get_json()
    except:
        return make_response("Error parsing data", 400)
    
    if not data:
        return make_response("Invalid data provided", 400)
    
    key = None
    try:
        for key, value in data.items():
            existing_setting = db.session.execute(db.Select(models.Settings).where(models.Settings.key == key)).scalar_one_or_none()
            if existing_setting is None:
                create_record(key=key, value=value)
            else:
                update_record(obj=existing_setting, value=value)
    except:
        return make_response(f"Error processing key: '{key}'", 500)
    
    return make_response("Success!", 200)

# I left these here as an example / for testing
# @settings_api_bp.route("/test/create-all")
# def test_create_all():
#     return requests.post("http://127.0.0.1:5000/api/settings/",
#                              headers = {'Content-type': 'application/json'},
#                              json={"str": "test",
#                                    "int": 1,
#                                    "float": 2.3,
#                                    "bool": True,
#                                    "dict": {"test": "me", "out": "!"}}
#                         ).text
# @settings_api_bp.route("/test/string")
# def test_string():
#     return requests.post("http://127.0.0.1:5000/api/settings/",
#                              headers = {'Content-type': 'application/json'},
#                              json={"str": "test2"}
#                         ).text