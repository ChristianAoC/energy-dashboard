from flask import Blueprint, make_response, request, jsonify#, session

import uuid
import os
# import openpyxl

import api.endpoints.data as data_api_bp
import api.settings as settings
from constants import *
from database import db, generate_offine_meta
import log
import models

settings_api_bp = Blueprint('metadata_api_bp', __name__, static_url_path='')

## Returns the data stored with the given key (or all records as a dict if no key is sent)
##
## Parameters:
## key - The key to search for, if not given we return all key-value pairs in a dict
##
## Example:
## http://127.0.0.1:5000/api/settings/
## http://127.0.0.1:5000/api/settings/?key=key
@settings_api_bp.route("/")
@settings_api_bp.route("")
@data_api_bp.required_user_level("USER_LEVEL_ADMIN")
def get():
    try:
        key = request.args["key"]
    except:
        key = None
    
    if key is None:
        result = db.session.execute(db.select(models.Settings)).scalars().all()
        out = []
        for entry in result:
            out.append(entry.to_dict())
        return make_response(jsonify(out), 200)
    
    result = db.session.execute(db.select(models.Settings).where(models.Settings.key == key)).scalar_one_or_none()
    if result is None:
        return make_response("Key not found", 404)
    return make_response(jsonify(result.value), 200)

## Creates/updates settings records 
##
## Send the data in the following format:
## json = {
##     key: {
##         "value": value,
##         "type": type,
##         "category": category
##     }
## }
##
## Example request (python requests format):
## requests.post("http://127.0.0.1:5000/api/settings/",
##               headers = {'Content-type': 'application/json'},
##               json={
##                   "str": {
##                       "value": "test",
##                       "type": "str",
##                       "category": "testing"
##                   },
##                   "int": {
##                       "value": 1,
##                       "type": "int",
##                       "category": "testing"
##                   },
##                   "float": {
##                       "value": 2.3,
##                       "type": "float",
##                       "category": "testing"
##                   },
##                   "bool": {
##                       "value": True,
##                       "type": "bool",
##                       "category": "testing"
##                   },
##                   "dict": {
##                       "value": {"test": "me", "out": "!"},
##                       "type": "dict",
##                       "category": "testing"
##               }
##              )
##
## Example:
## http://127.0.0.1:5000/api/settings/
@settings_api_bp.route("/", methods=["POST"])
@settings_api_bp.route("", methods=["POST"])
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
            
            if type(value) is not dict and existing_setting is None:
                setting_value = value
                setting_type = type(value).__name__
                category = None
            elif type(value) is not dict and existing_setting is not None:
                setting_value = value
                setting_type = type(value).__name__
                category = existing_setting.category
            else:
                setting_value = value["value"]
                setting_type = value["type"]
                category = value.get("category")
            
            if existing_setting is None:
                settings.create_record(key=key, value=setting_value, setting_type=setting_type, category=category)
            else:
                settings.update_record(obj=existing_setting, value=setting_value, setting_type=setting_type, category=category)
    except Exception as e:
        log.write(msg=f"Error processing key: '{key}'", extra_info=str(e), level=log.error)
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

@settings_api_bp.route("/upload/metadata/", methods=["POST"])
@settings_api_bp.route("/upload/metadata", methods=["POST"])
@data_api_bp.required_user_level("USER_LEVEL_ADMIN")
def upload_metadata():
    if 'file' not in request.files:
        return make_response("Invalid data", 400)
    
    file = request.files['file']
    if not file or file.filename == '':
        return make_response("Invalid data", 400)
    
    if file.content_type != "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
        response = make_response("Invalid data", 415)
        response.headers["Accept-Post"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        return response
    
    filename = str(file.filename)
    
    if not ("." in filename and filename.rsplit(".", 1)[1].lower() == "xlsx"):
        return make_response("Invalid data", 415)
    
    try:
        os.makedirs(os.path.dirname(metadata_file), exist_ok=True)
        tempfile = os.path.join(os.path.dirname(metadata_file), str(uuid.uuid4()))
        file.save(tempfile, buffer_size=1048576) # Allow files up to 1 Mebibyte in size
        os.replace(tempfile, metadata_file)
        settings.process_metadata_update()
    except Exception as e:
        log.write(msg="Failed to save or process new metadata", extra_info=str(e), level=log.error)
        return make_response("Error saving file", 500)
    return make_response("OK", 200)

@settings_api_bp.route("/upload/benchmarks/", methods=["POST"])
@settings_api_bp.route("/upload/benchmarks", methods=["POST"])
@data_api_bp.required_user_level("USER_LEVEL_ADMIN")
def upload_benchmark():
    if 'file' not in request.files:
        return make_response("Invalid data", 400)
    
    file = request.files['file']
    if not file or file.filename == '':
        return make_response("Invalid data", 400)
    
    if file.content_type != "application/json":
        response = make_response("Invalid data", 415)
        response.headers["Accept-Post"] = "application/json"
        return response
    
    filename = str(file.filename)
    
    if not ("." in filename and filename.rsplit(".", 1)[1].lower() == "json"):
        return make_response("Invalid data", 415)
    
    try:
        os.makedirs(os.path.dirname(benchmark_data_file), exist_ok=True)
        tempfile = os.path.join(os.path.dirname(benchmark_data_file), str(uuid.uuid4()))
        file.save(tempfile)
        os.replace(tempfile, benchmark_data_file)
        settings.invalidate_summary_cache()
    except:
        return make_response("Error saving file", 500)
    return make_response("OK", 200)

@settings_api_bp.route("/upload/polygons/", methods=["POST"])
@settings_api_bp.route("/upload/polygons", methods=["POST"])
@data_api_bp.required_user_level("USER_LEVEL_ADMIN")
def upload_polygons():
    if 'file' not in request.files:
        return make_response("Invalid data", 400)
    
    file = request.files['file']
    if not file or file.filename == '':
        return make_response("Invalid data", 400)
    
    if file.content_type != "application/json":
        response = make_response("Invalid data", 415)
        response.headers["Accept-Post"] = "application/json"
        return response
    
    filename = str(file.filename)
    
    if not ("." in filename and filename.rsplit(".", 1)[1].lower() == "json"):
        return make_response("Invalid data", 415)
    
    try:
        os.makedirs(os.path.dirname(mazemap_polygons_file), exist_ok=True)
        tempfile = os.path.join(os.path.dirname(mazemap_polygons_file), str(uuid.uuid4()))
        file.save(tempfile)
        os.replace(tempfile, mazemap_polygons_file)
    except:
        return make_response("Error saving file", 500)
    return make_response("OK", 200)

@settings_api_bp.route("/regenerate-offline-metadata/", methods=["GET", "POST"])
@settings_api_bp.route("/regenerate-offline-metadata", methods=["GET", "POST"])
@data_api_bp.required_user_level("USER_LEVEL_ADMIN")
def regenerate_offline_metadata():
    if generate_offine_meta():
        return make_response("OK", 200)
    return make_response("ERROR", 500)

## This is the start of a more guided upload for metadata
# @settings_api_bp.route("/upload/new", methods=["POST"])
# @data_api_bp.required_user_level("USER_LEVEL_ADMIN")
# def upload_new():
#     if 'file' not in request.files:
#         return make_response("Invalid data", 400)
    
#     file = request.files['file']
#     if not file or file.filename == '':
#         return make_response("Invalid data", 400)
    
#     if file.content_type != "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
#         response = make_response("Invalid data", 415)
#         response.headers["Accept-Post"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
#         return response
    
#     filename = str(file.filename)
    
#     if not ("." in filename and filename.rsplit(".", 1)[1].lower() == "xlsx"):
#         return make_response("Invalid data", 415)
#     cleaned_filename = f"{str(uuid.uuid4())}.xlsx"
#     folder_path = os.path.join(upload_folder, "metadata_upload")
    
#     os.makedirs(folder_path, exist_ok=True)
    
#     file_path = os.path.join(folder_path, cleaned_filename)
    
#     if os.path.exists(file_path):
#         os.remove(file_path)
    
#     try:
#         file.save(file_path)
#     except:
#         return make_response("Error saving file", 500)
    
#     session["metadata_upload_filename"] = cleaned_filename
#     return make_response("OK", 200)

# @settings_api_bp.route("/upload/sheets", methods=["GET"])
# @data_api_bp.required_user_level("USER_LEVEL_ADMIN")
# def upload_sheets_get():
#     try:
#         filename = session["metadata_upload_filename"]
#     except:
#         return make_response("Upload the file first", 400)
    
#     cleaned_filename = secure_filename(filename)
#     file_path = os.path.join(upload_folder, "metadata_upload", cleaned_filename)
    
#     if not os.path.exists(file_path):
#         return make_response("Invalid file", 404)
    
#     results = openpyxl.load_workbook(file_path).sheetnames
    
#     return make_response(jsonify(results), 200)

# @settings_api_bp.route("/upload/sheets", methods=["POST"])
# @data_api_bp.required_user_level("USER_LEVEL_ADMIN")
# def upload_sheets_post():
#     try:
#         filename = session["metadata_upload_filename"]
#     except:
#         return make_response("Upload the file first", 400)
    
#     try:
#         data = request.get_json()
#     except:
#         return make_response("Error parsing data", 400)
    
#     cleaned_filename = secure_filename(filename)
#     file_path = os.path.join(upload_folder, cleaned_filename)
    
#     if not os.path.exists(file_path):
#         return make_response("Invalid filename", 404)
    
#     results = openpyxl.load_workbook(file_path).sheetnames
    
#     return make_response(jsonify(results), 200)