from flask import Blueprint, make_response, request, jsonify, g

import api.context as context
import api.endpoints.data as data_api_bp
import api.users as users
import log

from datetime import datetime


context_api_bp = Blueprint('context_api_bp', __name__, static_url_path='')

###########################################################
###               context functionality                 ###
###########################################################

@context_api_bp.route("/add/", methods=['POST'])
@context_api_bp.route("/add", methods=['POST'])
@data_api_bp.required_user_level("user_level_submit_comments")
def add_context():
    context_elem = request.json
    if context_elem is None:
        return make_response("Invalid context", 400)
    
    cookies = request.cookies
    email = cookies.get("Email", None)
    session_id = cookies.get("SessionID", None)
    
    # for global mute run user level check just to be sure
    if context_elem["type"] == "Global-mute":
        if users.get_user_level(email, session_id) < g.settings["user_level_edit_comments"]:
            return make_response("Unauthorised", 403)
    
    # Check that the author is the current user, only admins can forge authorship
    if context_elem["author"] != email:
        if users.get_user_level(email, session_id) < g.settings["user_level_admin"]:
            return make_response("Unauthorised", 403)
        start_time = context_elem.get("start")
        if start_time is not None:
            start_time = datetime.strptime(start_time,"%Y-%m-%d %H:%M")
        start_timestamp = start_time

        end_time = context_elem.get("end")
        if end_time is not None:
            end_time = datetime.strptime(end_time,"%Y-%m-%d %H:%M")
        end_timestamp = end_time
        
        log_msg = f"WARNING: User {email} forged authorship of {context_elem['author']} for the following context item:"
        log_extra_info = f"target_type={context_elem['target_type'].lower()};target_id={context_elem['target_id']};context_type={context_elem['type']};start_timestamp={start_timestamp};end_timestamp={end_timestamp};deleted={context_elem.get('deleted', False)}"
        log.write(msg=log_msg, level=log.warning, extra_info=log_extra_info)
        print(log_msg)
        print(log_extra_info)
    
    return context.add_context(context_elem)

@context_api_bp.route("/edit/", methods=['POST'])
@context_api_bp.route("/edit", methods=['POST'])
@data_api_bp.required_user_level("user_level_submit_comments")
def edit_context():
    context_elem = request.json
    if not context_elem:
        return make_response("Missing context element", 400)
    if context_elem["type"] == "Global-mute":
        cookies = request.cookies
        email = cookies.get("Email", None)
        session_id = cookies.get("SessionID", None)
        if users.get_user_level(email, session_id) < 4:
            return make_response("Unauthorised", 403)
    return context.edit_context(context_elem)

@context_api_bp.route("/delete/", methods=['POST'])
@context_api_bp.route("/delete", methods=['POST'])
@data_api_bp.required_user_level("user_level_submit_comments")
def delete_context():
    context_id = request.args.get('contextID')
    if not context_id:
        return make_response("Missing contextID", 400)
    cookies = request.cookies
    email = cookies.get("Email", None)
    session_id = cookies.get("SessionID", None)
    if email is None or session_id is None:
        return make_response("Unauthorised", 401)
    user_level = users.get_user_level(email, session_id)
    if user_level < 4:
        return make_response("Unauthorised", 403)
    return context.delete_context(context_id)

@context_api_bp.route("/all/")
@context_api_bp.route("/all")
@data_api_bp.required_user_level("user_level_view_comments")
def get_context():
    return make_response(jsonify(context.view_all()), 200)