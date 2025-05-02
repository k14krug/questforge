from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify # Added jsonify back
from flask_login import login_required, current_user
import json # Import json for parsing/dumping
from ..models.template import Template
from ..extensions import db
from ..views.forms import TemplateForm

template_bp = Blueprint('template', __name__)

@template_bp.route('/templates')
@login_required
def list_templates():
    """List all available templates"""
    # fix_question_flow() # Removed call to potentially conflicting data fixing function
    templates = Template.query.filter_by(created_by=current_user.id).all()
    return render_template('template/list.html', templates=templates)

@template_bp.route('/template/create', methods=['GET', 'POST'])
@login_required
def create_template():
    """Create a new template"""
    form = TemplateForm()

    # Removed default value setting for old JSON fields

    if form.validate_on_submit():
        # Instantiate Template with new fields directly from the form
        template = Template(
            name=form.name.data,
            description=form.description.data,
            created_by=current_user.id,
            category=form.category.data,
            genre=form.genre.data,
            core_conflict=form.core_conflict.data,
            theme=form.theme.data,
            desired_tone=form.desired_tone.data,
            world_description=form.world_description.data,
            scene_suggestions=form.scene_suggestions.data,
            player_character_guidance=form.player_character_guidance.data,
            difficulty=form.difficulty.data,
            estimated_length=form.estimated_length.data,
            ai_service_endpoint=form.ai_service_endpoint.data
        )
        
        db.session.add(template)
        db.session.commit()
        flash('Template created successfully!', 'success')
        return redirect(url_for('template.list_templates'))
        # Removed JSON parsing and related error handling
        
    return render_template('template/create.html', form=form)

@template_bp.route('/template/<int:template_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_template(template_id):
    """Edit an existing template"""
    template = Template.query.get_or_404(template_id)
    
    if template.created_by != current_user.id:
        flash('You can only edit your own templates', 'danger')
        return redirect(url_for('template.list_templates'))

    # Use obj=template for initial population of simple fields on GET
    # Use obj=template for initial population of simple fields on GET
    form = TemplateForm(obj=template)

    if form.validate_on_submit(): # Process POST request
        # Update template object with data from the new form fields
        template.name = form.name.data
        template.description = form.description.data
        template.category = form.category.data
        template.genre = form.genre.data
        template.core_conflict = form.core_conflict.data
        template.theme = form.theme.data
        template.desired_tone = form.desired_tone.data
        template.world_description = form.world_description.data
        template.scene_suggestions = form.scene_suggestions.data
        template.player_character_guidance = form.player_character_guidance.data
        template.difficulty = form.difficulty.data
        template.estimated_length = form.estimated_length.data
        template.ai_service_endpoint = form.ai_service_endpoint.data

        db.session.commit() # Save all changes
        flash('Template updated successfully!', 'success')
        return redirect(url_for('template.list_templates'))
        # Removed JSON parsing and related error handling

    # Render the form for GET request (or if validation failed on POST)
    return render_template('template/edit.html', form=form, template=template)

@template_bp.route('/template/<int:template_id>/delete', methods=['POST'])
@login_required
def delete_template(template_id):
    """Delete a template"""
    template = Template.query.get_or_404(template_id)
    
    if template.created_by != current_user.id:
        flash('You can only delete your own templates', 'danger')
        return redirect(url_for('template.list_templates'))
        
    db.session.delete(template)
    db.session.commit()
    flash('Template deleted successfully', 'success')
    return redirect(url_for('template.list_templates'))


# Removed potentially conflicting data fixing function
# @template_bp.route('/template/fix_question_flow')
# @login_required
# def fix_question_flow():
#     """Temporary route to fix question_flow data in templates"""
#     templates = Template.query.filter_by(created_by=current_user.id).all()
    
#     for template in templates:
#         try:
#             if isinstance(template.question_flow, dict):
#                 # If it's already a dict, skip parsing
#                 question_flow = template.question_flow
#             else:
#                 question_flow = json.loads(template.question_flow)
#                 if isinstance(question_flow, list):
#                     new_question_flow = {str(i): q for i, q in enumerate(question_flow)}
#                     template.question_flow = new_question_flow
#                     db.session.add(template)
#         except (TypeError, json.JSONDecodeError):
#             # Handle cases where question_flow is None or not a valid JSON string
#             pass
            
#     db.session.commit()
#     flash('Question flow data fixed successfully!', 'success')
#     return redirect(url_for('template.list_templates'))

# --- API Endpoint for Template Details ---

@template_bp.route('/api/templates/<int:template_id>/details', methods=['GET'])
@login_required # Ensure only logged-in users can access
def get_template_details(template_id):
    """API endpoint to get the full details for a specific template."""
    template = Template.query.get_or_404(template_id)
    
    # Return template details as JSON
    return jsonify({
        'id': template.id,
        'name': template.name,
        'description': template.description,
        'category': template.category,
        'genre': template.genre,
        'core_conflict': template.core_conflict,
        'theme': template.theme,
        'desired_tone': template.desired_tone,
        'world_description': template.world_description,
        'scene_suggestions': template.scene_suggestions,
        'player_character_guidance': template.player_character_guidance,
        'difficulty': template.difficulty,
        'estimated_length': template.estimated_length,
        'default_rules': template.default_rules, # Include default_rules
        'ai_service_endpoint': template.ai_service_endpoint
    })
