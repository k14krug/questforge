from flask import Flask
from flask_migrate import Migrate
import click
from questforge import create_app
from questforge.extensions import db

app = create_app()
migrate = Migrate(app, db)

@click.group()
def cli():
    """Management script for the QuestForge application."""
    pass

@cli.command()
def initdb():
    """Initialize the database."""
    db.create_all()
    click.echo('Initialized the database.')

# Import the migration commands
from flask_migrate.cli import db

# Add the db command group
cli.add_command(db)

if __name__ == '__main__':
    cli()