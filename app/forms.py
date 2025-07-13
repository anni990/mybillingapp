from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, SubmitField
from wtforms.validators import DataRequired, Email, Length

class EmployeeRegistrationForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(max=100)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=100)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6, max=100)])
    shop_id = SelectField('Shop Name', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Add Employee')

class EmployeeEditForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(max=100)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=100)])
    password = PasswordField('Password', validators=[Length(min=0, max=100)])  # Optional
    shop_id = SelectField('Shop Name', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Update Employee')

class CAProfileForm(FlaskForm):
    firm_name = StringField('Firm Name', validators=[DataRequired(), Length(max=100)])
    area = StringField('Area/Location', validators=[DataRequired(), Length(max=100)])
    contact_number = StringField('Contact Number', validators=[DataRequired(), Length(max=20)])
    gst_number = StringField('GST Number', validators=[Length(max=20)])
    pan_number = StringField('PAN Number', validators=[Length(max=20)])
    address = StringField('Address', validators=[Length(max=255)])
    submit = SubmitField('Update Profile')
