from flask import Blueprint, make_response, request, jsonify, session, current_app
from werkzeug.utils import secure_filename

import api.endpoints.data as data_api_bp
from constants import *
from database import db
import models
import uuid
import os
# import openpyxl

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
        tempfile = os.path.join(os.path.dirname(metadata_file), str(uuid.uuid4()))
        file.save(tempfile, buffer_size=1048576) # Allow files up to 1 Mebibyte in size
        os.replace(tempfile, metadata_file)
    except:
        return make_response("Error saving file", 500)
    return make_response("OK", 200)

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
        tempfile = os.path.join(os.path.dirname(benchmark_data_file), str(uuid.uuid4()))
        file.save(tempfile)
        os.replace(tempfile, benchmark_data_file)
    except:
        return make_response("Error saving file", 500)
    return make_response("OK", 200)

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
        tempfile = os.path.join(os.path.dirname(mazemap_polygons_file), str(uuid.uuid4()))
        file.save(tempfile)
        os.replace(tempfile, mazemap_polygons_file)
    except:
        return make_response("Error saving file", 500)
    return make_response("OK", 200)


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