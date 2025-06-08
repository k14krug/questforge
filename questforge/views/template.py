from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from sqlalchemy.orm.attributes import flag_modified

def mark_json_changed(target, attribute):
    """Force SQLAlchemy to detect changes to JSON fields"""
    flag_modified(target, attribute)
from flask_login import login_required, current_user
import json # Import json for parsing/dumping
from ..models.template import Template
from ..extensions import db
from ..views.forms import TemplateForm

# Define the mapping from abbreviation to full name for puzzle types
PUZZLE_TYPE_MAP = {
    'r': 'Logic/Riddle',
    'i': 'Inventory/Environmental',
    'd': 'Social/Dialogue', # Assuming 'd' for Dialogue/Deduction
    'l': 'Logic/Riddle', # 'l' for Logic
    'e': 'Environmental/Physical', # 'e' for Environmental
    'p': 'Procedural/Sequence', # 'p' for Procedural
    'h': 'Hidden Objects', # 'h' for Hidden Objects
    'c': 'Code Breaking' # 'c' for Code Breaking
}

template_bp = Blueprint('template', __name__)

def log_template_routes(app):
    """Log registered template routes after app initialization"""
    with app.app_context():
        print(f"\n\n=== TEMPLATE ROUTES REGISTERED ===\nRoutes:")
        for rule in app.url_map.iter_rules():
            if rule.endpoint.startswith('template.'):
                print(f"- {rule}")
        print("\n")

@template_bp.route('/templates')
@login_required
def list_templates():
    """List all available templates"""
    templates = Template.query.filter_by(created_by=current_user.id).all()
    return render_template('template/list.html', templates=templates)

@template_bp.route('/template/create', methods=['GET', 'POST'])
@login_required
def create_template():
    """Create a new template"""
    form = TemplateForm()

    if form.validate_on_submit():
        # Map abbreviated puzzle types from form to full names for storage
        mapped_enabled_types = [PUZZLE_TYPE_MAP.get(t, t) for t in form.puzzle_types.data]

        puzzle_config = {
            "enabled": form.enable_puzzles.data,
            "enabled_types": mapped_enabled_types,
            "global_puzzle_difficulty": form.puzzle_difficulty.data,
            "puzzle_frequency": form.puzzle_frequency.data,
            "hint_frequency": form.hint_frequency.data,
            "failure_consequences": form.puzzle_difficulty.data
        }

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
            ai_service_endpoint=form.ai_service_endpoint.data,
            default_rules={"puzzles": puzzle_config}
        )
        
        db.session.add(template)
        db.session.commit()
        flash('Template created successfully!', 'success')
        return redirect(url_for('template.list_templates'))
        
    return render_template('template/create.html', form=form)

@template_bp.route('/template/<int:template_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_template(template_id):
    """Edit an existing template"""
    template = Template.query.get_or_404(template_id)
    
    if template.created_by != current_user.id:
        flash('You can only edit your own templates', 'danger')
        return redirect(url_for('template.list_templates'))

    if request.method == 'POST':
        form = TemplateForm(request.form) # Populate form with submitted data

        if not form.is_submitted():
            if 'submit' not in request.form:
                flash('Please submit the form using the Update Template button', 'error')
            else:
                flash('Invalid form submission. Please try again.', 'error')
            return render_template('template/edit.html', form=form, template=template)

        if form.validate_on_submit():
            # Update puzzle configuration
            if not template.default_rules:
                template.default_rules = {}
                
            # Map abbreviated puzzle types from form to full names for storage
            mapped_enabled_types = [PUZZLE_TYPE_MAP.get(str(t), str(t)) for t in form.puzzle_types.data]

            puzzle_config = {
                "enabled": bool(form.enable_puzzles.data),
                "enabled_types": mapped_enabled_types,
                "global_puzzle_difficulty": str(form.puzzle_difficulty.data),
                "puzzle_frequency": str(form.puzzle_frequency.data),
                "hint_frequency": str(form.hint_frequency.data),
                "failure_consequences": str(form.puzzle_difficulty.data)
            }
            
            template.default_rules["puzzles"] = puzzle_config
            mark_json_changed(template, 'default_rules')
            db.session.add(template)
            
            # Update other template fields
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

            try:
                db.session.commit() # Save all changes
                
                flash('Template updated successfully!', 'success')
                return redirect(url_for('template.list_templates'))
            except Exception as e:
                db.session.rollback()
                flash('Failed to update template. Please try again.', 'danger')
                return render_template('template/edit.html', form=form, template=template)
        else:
            # Render the form if validation failed on POST
            return render_template('template/edit.html', form=form, template=template)

    # GET request handling
    form = TemplateForm(obj=template) # Populate form with template object for GET
    
    # Then manually set puzzle fields from default_rules with proper type conversion and reverse mapping
    if template.default_rules and 'puzzles' in template.default_rules:
        puzzles = template.default_rules['puzzles']
        form.enable_puzzles.data = bool(puzzles.get('enabled', False))
        enabled_types = puzzles.get('enabled_types', [])
        
        # Ensure enabled_types is always a list of strings for processing
        if isinstance(enabled_types, str):
             enabled_types = [enabled_types]
        elif not isinstance(enabled_types, list):
             enabled_types = []

        # Apply reverse mapping: map full names back to abbreviations for the form
        reverse_map = {v: k for k, v in PUZZLE_TYPE_MAP.items()}
        form.puzzle_types.data = [reverse_map.get(str(t), str(t)) for t in enabled_types]

        form.puzzle_difficulty.data = str(puzzles.get('global_puzzle_difficulty', 'medium'))
        form.puzzle_frequency.data = str(puzzles.get('puzzle_frequency', 'moderate'))
        form.hint_frequency.data = str(puzzles.get('hint_frequency', 'moderate'))

    return render_template('template/edit.html', form=form, template=template)
    print(f"DEBUG: Before rendering template - form.puzzle_types.choices: {form.puzzle_types.choices}")


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
