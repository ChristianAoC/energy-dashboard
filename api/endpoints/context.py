from flask import Blueprint, make_response, request, jsonify, g

import api.context as context
import api.endpoints.data as data_api_bp
import api.users as users

context_api_bp = Blueprint('context_api_bp', __name__, static_url_path='')

###########################################################
###               context functionality                 ###
###########################################################

@context_api_bp.route("/add/", methods=['POST'])
@context_api_bp.route("/add", methods=['POST'])
@data_api_bp.required_user_level("USER_LEVEL_SUBMIT_COMMENTS")
def add_context():
    context_elem = request.json
    if context_elem is None:
        return make_response("Invalid context", 400)
    
    # for global mute run user level check just to be sure
    if context_elem["type"] == "Global-mute":
        cookies = request.cookies
        email = cookies.get("Email", None)
        session_id = cookies.get("SessionID", None)
        if users.get_user_level(email, session_id) < g.settings["USER_LEVEL_EDIT_COMMENTS"]:
            return make_response("Unauthorised", 401)
    
    return context.add_context(context_elem)

@context_api_bp.route("/edit/", methods=['POST'])
@context_api_bp.route("/edit", methods=['POST'])
@data_api_bp.required_user_level("USER_LEVEL_SUBMIT_COMMENTS")
def edit_context():
    context_elem = request.json
    if not context_elem:
        return make_response("Missing context element", 400)
    if context_elem["type"] == "Global-mute":
        cookies = request.cookies
        email = cookies.get("Email", None)
        session_id = cookies.get("SessionID", None)
        if users.get_user_level(email, session_id) < 4:
            return make_response("Unauthorised", 401)
    return context.edit_context(context_elem)

@context_api_bp.route("/delete/", methods=['POST'])
@context_api_bp.route("/delete", methods=['POST'])
@data_api_bp.required_user_level("USER_LEVEL_SUBMIT_COMMENTS")
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
        return make_response("Unauthorised", 401)
    return context.delete_context(context_id)

@context_api_bp.route("/all/")
@context_api_bp.route("/all")
@data_api_bp.required_user_level("USER_LEVEL_VIEW_COMMENTS")
def get_context():
    return make_response(jsonify(context.view_all()), 200)