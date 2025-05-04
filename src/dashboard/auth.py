from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Length
import os
from datetime import datetime

from src.config import config
from src.database.models import User, get_session

# Create blueprint
auth = Blueprint('auth', __name__)

# Initialize login manager
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = "Please log in to access this page."

@login_manager.user_loader
def load_user(user_id):
    """Load user by ID."""
    session = get_session()
    user = session.query(User).get(int(user_id))
    session.close()
    return user

# Login form
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

# Password change form
class PasswordChangeForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[
        DataRequired(),
        Length(min=8, message='Password must be at least 8 characters long')
    ])
    confirm_password = PasswordField('Confirm New Password', validators=[
        DataRequired(),
        EqualTo('new_password', message='Passwords must match')
    ])
    submit = SubmitField('Change Password')

# User settings form
class UserSettingsForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Update Settings')

@auth.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    form = LoginForm()
    if form.validate_on_submit():
        session = get_session()
        user = session.query(User).filter_by(username=form.username.data).first()
        
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password', 'danger')
            session.close()
            return redirect(url_for('auth.login'))

        # Update last login time
        user.last_login = datetime.utcnow()
        session.commit()
        
        login_user(user, remember=form.remember_me.data)
        session.close()
        
        next_page = request.args.get('next')
        if not next_page or not next_page.startswith('/'):
            next_page = url_for('dashboard.index')

        return redirect(next_page)

    return render_template('login.html', title='Sign In', form=form)

@auth.route('/logout')
def logout():
    """Handle user logout."""
    logout_user()
    return redirect(url_for('auth.login'))

@auth.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    """
    Change user password
    """
    form = PasswordChangeForm()

    if form.validate_on_submit():
        # Verify current password
        if not current_user.check_password(form.current_password.data):
            flash('Current password is incorrect', 'danger')
            return render_template('change_password.html', title='Change Password', form=form)

        # Update password in database
        session = get_session()
        user = session.query(User).get(current_user.id)
        user.set_password(form.new_password.data)
        session.commit()
        session.close()

        # Also update in config file for admin user if this is the admin
        if current_user.is_admin:
            try:
                # Update .env file
                with open('.env', 'r') as f:
                    env_content = f.read()

                # Replace the password line
                import re
                new_env_content = re.sub(
                    r'DASHBOARD_PASSWORD=.*',
                    f'DASHBOARD_PASSWORD={form.new_password.data}',
                    env_content
                )

                with open('.env', 'w') as f:
                    f.write(new_env_content)
            except Exception as e:
                flash(f'Password updated in database but not in .env file: {str(e)}', 'warning')

        flash('Password changed successfully!', 'success')
        return redirect(url_for('dashboard.settings'))

    return render_template('change_password.html', title='Change Password', form=form)

@auth.route('/user_settings', methods=['GET', 'POST'])
@login_required
def user_settings():
    """
    Update user settings
    """
    form = UserSettingsForm()

    # Pre-populate form with current user data
    if request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email

    if form.validate_on_submit():
        # Check if username is changed and already exists
        session = get_session()
        
        if form.username.data != current_user.username:
            existing_user = session.query(User).filter_by(username=form.username.data).first()
            if existing_user:
                session.close()
                flash('Username already exists', 'danger')
                return render_template('user_settings.html', title='User Settings', form=form)
        
        # Check if email is changed and already exists
        if form.email.data != current_user.email:
            existing_user = session.query(User).filter_by(email=form.email.data).first()
            if existing_user:
                session.close()
                flash('Email already exists', 'danger')
                return render_template('user_settings.html', title='User Settings', form=form)
                
        # Update user in database
        user = session.query(User).get(current_user.id)
        user.username = form.username.data
        user.email = form.email.data
        session.commit()

        # If this is the admin user, also update the .env file
        if user.is_admin:
            try:
                # Update .env file
                with open('.env', 'r') as f:
                    env_content = f.read()

                # Replace the username line
                import re
                new_env_content = re.sub(
                    r'DASHBOARD_USERNAME=.*',
                    f'DASHBOARD_USERNAME={form.username.data}',
                    env_content
                )

                with open('.env', 'w') as f:
                    f.write(new_env_content)
            except Exception as e:
                flash(f'User settings updated in database but not in .env file: {str(e)}', 'warning')

        session.close()
        flash('User settings updated successfully!', 'success')
        return redirect(url_for('dashboard.settings'))

    return render_template('user_settings.html', title='User Settings', form=form)
