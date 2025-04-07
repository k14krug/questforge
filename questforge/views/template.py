from flask import Blueprint, render_template, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
import json
from ..models.template import Template
from ..extensions import db
from ..views.forms import TemplateForm

template_bp = Blueprint('template', __name__)

@template_bp.route('/templates')
@login_required
def list_templates():
    """List all available templates"""
    fix_question_flow()
    templates = Template.query.filter_by(created_by=current_user.id).all()
    return render_template('template/list.html', templates=templates)

@template_bp.route('/template/create', methods=['GET', 'POST'])
@login_required
def create_template():
    """Create a new template"""
    form = TemplateForm()
    
    if form.validate_on_submit():
        try:
            template = Template(
                name=form.name.data,
                description=form.description.data,
                created_by=current_user.id,
                category=form.category.data,
                question_flow=json.loads(form.question_flow.data),
                default_rules=json.loads(form.default_rules.data),
                ai_service_endpoint=form.ai_service_endpoint.data,
                initial_state={
                    'campaign_data': json.loads(form.campaign_data.data),
                    'objectives': json.loads(form.objectives.data),
                    'conclusion_conditions': json.loads(form.conclusion_conditions.data),
                    'key_locations': json.loads(form.key_locations.data),
                    'key_characters': json.loads(form.key_characters.data),
                    'major_plot_points': json.loads(form.major_plot_points.data),
                    'possible_branches': json.loads(form.possible_branches.data)
                }
            )
            if not template.validate_question_flow():
                flash('Invalid question flow structure.', 'danger')
                return render_template('template/create.html', form=form)
            db.session.add(template)
            db.session.commit()
            flash('Template created successfully!', 'success')
            return redirect(url_for('template.list_templates'))
        except json.JSONDecodeError:
            flash('Invalid JSON format in one or more fields.', 'danger')
            return render_template('template/create.html', form=form)
        
    return render_template('template/create.html', form=form)

@template_bp.route('/template/<int:template_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_template(template_id):
    """Edit an existing template"""
    template = Template.query.get_or_404(template_id)
    
    if template.created_by != current_user.id:
        flash('You can only edit your own templates', 'danger')
        return redirect(url_for('template.list_templates'))
        
    # Populate form with template data including initial_state
    form = TemplateForm(obj=template)
    if template.initial_state:
        form.campaign_data.data = template.initial_state.get('campaign_data', '')
        form.objectives.data = template.initial_state.get('objectives', '')
        form.conclusion_conditions.data = template.initial_state.get('conclusion_conditions', '')
        form.key_locations.data = template.initial_state.get('key_locations', '')
        form.key_characters.data = template.initial_state.get('key_characters', '')
        form.major_plot_points.data = template.initial_state.get('major_plot_points', '')
        form.possible_branches.data = template.initial_state.get('possible_branches', '')
    
    if form.validate_on_submit():
        try:
            form.populate_obj(template)
            template.question_flow = json.loads(form.question_flow.data)
            template.default_rules = json.loads(form.default_rules.data)
            template.initial_state = {
                'campaign_data': json.loads(form.campaign_data.data),
                'objectives': json.loads(form.objectives.data),
                'conclusion_conditions': json.loads(form.conclusion_conditions.data),
                'key_locations': json.loads(form.key_locations.data),
                'key_characters': json.loads(form.key_characters.data),
                'major_plot_points': json.loads(form.major_plot_points.data),
                'possible_branches': json.loads(form.possible_branches.data)
            }
            if not template.validate_question_flow():
                flash('Invalid question flow structure.', 'danger')
                return render_template('template/edit.html', form=form, template=template)
            db.session.commit()
            flash('Template updated successfully!', 'success')
            return redirect(url_for('template.list_templates'))
        except json.JSONDecodeError:
            flash('Invalid JSON format in one or more fields.', 'danger')
            return render_template('template/edit.html', form=form, template=template)
        
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

@template_bp.route('/api/template/<int:template_id>/questions')
@login_required
def get_raw_template_questions(template_id):
    """Get template questions for game creation"""
    template = Template.query.get_or_404(template_id)
    
    if not template.question_flow:
        return jsonify({'status': 'error', 'message': 'No questions defined for this template'}), 404
    
    return jsonify({
        'status': 'success',
        'template_name': template.name,
        'template_description': template.description,
        'questions': template.question_flow.get('questions', [])
    })

@template_bp.route('/template/fix_question_flow')
@login_required
def fix_question_flow():
    """Temporary route to fix question_flow data in templates"""
    templates = Template.query.filter_by(created_by=current_user.id).all()
    
    for template in templates:
        try:
            if isinstance(template.question_flow, dict):
                # If it's already a dict, skip parsing
                question_flow = template.question_flow
            else:
                question_flow = json.loads(template.question_flow)
                if isinstance(question_flow, list):
                    new_question_flow = {str(i): q for i, q in enumerate(question_flow)}
                    template.question_flow = new_question_flow
                    db.session.add(template)
        except (TypeError, json.JSONDecodeError):
            # Handle cases where question_flow is None or not a valid JSON string
            pass
            
    db.session.commit()
    flash('Question flow data fixed successfully!', 'success')
    return redirect(url_for('template.list_templates'))
