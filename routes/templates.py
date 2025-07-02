from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from database import db # Import db directly from database
from models import Template, User # Import Template and User models
from datetime import datetime

templates_bp = Blueprint('templates', __name__)

# Helper function to check template ownership
def check_template_ownership(template_id, user_id_str):
    user_id = int(user_id_str) # Convert JWT identity (string) to int
    template = Template.query.get(template_id)
    if not template:
        return None, {"msg": "Template not found"}, 404
    if template.created_by_user_id != user_id:
        return None, {"msg": "Unauthorized: You do not own this template"}, 403
    return template, None, None

@templates_bp.route('/api/templates', methods=['POST'])
@jwt_required()
def create_template():
    user_id_str = get_jwt_identity()
    user_id = int(user_id_str) # Convert JWT identity (string) to int
    data = request.get_json()

    name = data.get('name')
    genre = data.get('genre')
    core_conflict = data.get('core_conflict')
    world_description = data.get('world_description')
    ai_gm_persona = data.get('ai_gm_persona')
    core_skills = data.get('core_skills')

    if not all([name, genre, core_conflict, world_description, ai_gm_persona, core_skills]):
        return jsonify({"msg": "Missing required fields"}), 400

    if not isinstance(core_skills, list):
        return jsonify({"msg": "core_skills must be a list"}), 400

    # Check if a template with the same name already exists for this user
    existing_template = Template.query.filter_by(name=name, created_by_user_id=user_id).first() # user_id is already int here
    if existing_template:
        return jsonify({"msg": "Template with this name already exists"}), 409

    new_template = Template(
        name=name,
        genre=genre,
        core_conflict=core_conflict,
        world_description=world_description,
        ai_gm_persona=ai_gm_persona,
        core_skills=core_skills,
        created_by_user_id=user_id
    )

    db.session.add(new_template)
    db.session.commit()

    return jsonify(new_template.to_dict()), 201

@templates_bp.route('/api/templates', methods=['GET'])
@jwt_required()
def get_all_templates():
    user_id_str = get_jwt_identity()
    user_id = int(user_id_str) # Convert JWT identity (string) to int
    templates = Template.query.filter_by(created_by_user_id=user_id).all()
    return jsonify([template.to_dict() for template in templates]), 200

@templates_bp.route('/api/templates/<int:template_id>', methods=['GET'])
@jwt_required()
def get_template(template_id):
    user_id_str = get_jwt_identity() # get_jwt_identity() returns a string
    template, error_response, status_code = check_template_ownership(template_id, user_id_str) # Pass the string
    if error_response:
        return jsonify(error_response), status_code
    return jsonify(template.to_dict()), 200

@templates_bp.route('/api/templates/<int:template_id>', methods=['PUT'])
@jwt_required()
def update_template(template_id):
    user_id_str = get_jwt_identity() # get_jwt_identity() returns a string
    template, error_response, status_code = check_template_ownership(template_id, user_id_str) # Pass the string
    if error_response:
        return jsonify(error_response), status_code

    data = request.get_json()
    template.name = data.get('name', template.name)
    template.genre = data.get('genre', template.genre)
    template.core_conflict = data.get('core_conflict', template.core_conflict)
    template.world_description = data.get('world_description', template.world_description)
    template.ai_gm_persona = data.get('ai_gm_persona', template.ai_gm_persona)
    
    core_skills = data.get('core_skills')
    if core_skills is not None:
        if not isinstance(core_skills, list):
            return jsonify({"msg": "core_skills must be a list"}), 400
        template.core_skills = core_skills

    db.session.commit()
    return jsonify(template.to_dict()), 200

@templates_bp.route('/api/templates/<int:template_id>', methods=['DELETE'])
@jwt_required()
def delete_template(template_id):
    user_id_str = get_jwt_identity() # get_jwt_identity() returns a string
    template, error_response, status_code = check_template_ownership(template_id, user_id_str) # Pass the string
    if error_response:
        return jsonify(error_response), status_code

    db.session.delete(template)
    db.session.commit()
    return jsonify({"msg": "Template deleted successfully"}), 200
