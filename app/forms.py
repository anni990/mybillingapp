from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, SubmitField, TextAreaField, SelectMultipleField
from wtforms.validators import DataRequired, Email, Length
from flask_wtf.file import FileField, FileAllowed

class EmployeeRegistrationForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(max=100)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=100)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6, max=100)])
    shop_id = SelectMultipleField('Shop Name(s)', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Add Employee')

class EmployeeEditForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(max=100)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=100)])
    password = PasswordField('Password', validators=[Length(min=0, max=100)])  # Optional
    shop_id = SelectMultipleField('Shop Name(s)', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Update Employee')

class CAProfileForm(FlaskForm):
    firm_name = StringField('Firm Name', validators=[DataRequired(), Length(max=100)])
    area = StringField('Area/Location', validators=[DataRequired(), Length(max=100)])
    contact_number = StringField('Contact Number', validators=[DataRequired(), Length(max=20)])
    gst_number = StringField('GST Number', validators=[Length(max=20)])
    pan_number = StringField('PAN Number', validators=[Length(max=20)])
    address = StringField('Address', validators=[Length(max=255)])
    about_me = TextAreaField('About Me', validators=[Length(max=2000)])
    city = StringField('City', validators=[Length(max=100)])
    state = StringField('State', validators=[Length(max=100)])
    pincode = StringField('Pincode', validators=[Length(max=20)])
    # New fields for document uploads and GSTIN
    aadhaar_file = FileField('Aadhaar (PDF/JPG/PNG)', validators=[FileAllowed(['pdf', 'jpg', 'jpeg', 'png'], 'PDF, JPG, PNG only!')])
    pan_file = FileField('PAN (PDF/JPG/PNG)', validators=[FileAllowed(['pdf', 'jpg', 'jpeg', 'png'], 'PDF, JPG, PNG only!')])
    icai_certificate_file = FileField('ICAI Membership Certificate', validators=[FileAllowed(['pdf', 'jpg', 'jpeg', 'png'], 'PDF, JPG, PNG only!')])
    cop_certificate_file = FileField('Certificate of Practice (COP)', validators=[FileAllowed(['pdf', 'jpg', 'jpeg', 'png'], 'PDF, JPG, PNG only!')])
    gstin = StringField('GSTIN', validators=[Length(max=30)])
    business_reg_file = FileField('Business Registration Document', validators=[FileAllowed(['pdf', 'jpg', 'jpeg', 'png'], 'PDF, JPG, PNG only!')])
    bank_details_file = FileField('Bank Details (Cheque/Passbook)', validators=[FileAllowed(['pdf', 'jpg', 'jpeg', 'png'], 'PDF, JPG, PNG only!')])
    photo_file = FileField('Photograph', validators=[FileAllowed(['jpg', 'jpeg', 'png'], 'JPG, PNG only!')])
    signature_file = FileField('Signature', validators=[FileAllowed(['jpg', 'jpeg', 'png'], 'JPG, PNG only!')])
    office_address_proof_file = FileField('Office Address Proof', validators=[FileAllowed(['pdf', 'jpg', 'jpeg', 'png'], 'PDF, JPG, PNG only!')])
    self_declaration_file = FileField('Self-declaration', validators=[FileAllowed(['pdf', 'jpg', 'jpeg', 'png'], 'PDF, JPG, PNG only!')])
    submit = SubmitField('Update Profile')
