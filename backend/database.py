from flask_sqlalchemy import SQLAlchemy

# Initialize the SQLAlchemy instance
db = SQLAlchemy()

# Profile Model
class Profile(db.Model):
    __tablename__ = "profile"

    id = db.Column(db.Integer, primary_key=True)
    operator = db.Column(db.String(100))
    contractor = db.Column(db.String(100))
    report_no = db.Column(db.String(50))
    well_pad_name = db.Column(db.String(100))
    field = db.Column(db.String(50))
    well_type_profile = db.Column(db.String(100))
    latitude_longitude = db.Column(db.String(100))
    environment = db.Column(db.String(50))
    gl_msl_m = db.Column(db.Float)
    unique_hash = db.Column(db.String(32), unique=True, nullable=False)

# General Data Model
class GeneralData(db.Model):
    __tablename__ = "general_data"

    profile_id = db.Column(db.Integer, db.ForeignKey("profile.id"), primary_key=True)
    rig_type_name = db.Column(db.String(255))
    rig_power = db.Column(db.String(255))
    kb_elevation = db.Column(db.String(255))
    midnight_depth = db.Column(db.String(255))
    progress = db.Column(db.String(255))
    proposed_td = db.Column(db.String(255))
    spud_date = db.Column(db.String(255))
    release_date = db.Column(db.String(255))
    planned_days = db.Column(db.String(255))
    days_from_rig_release = db.Column(db.String(255))

# Drilling Parameters Model
class DrillingParameter(db.Model):
    __tablename__ = "drilling_parameters"

    profile_id = db.Column(db.Integer, db.ForeignKey("profile.id"), primary_key=True)
    average_wob_24_hrs = db.Column(db.String(255))
    average_rop_24_hrs = db.Column(db.String(255))
    average_surface_rpm_dhm = db.Column(db.String(255))
    on_off_bottom_torque = db.Column(db.String(255))
    flowrate_spp = db.Column(db.String(255))
    air_rate = db.Column(db.String(255))
    corr_inhib_foam_rate = db.Column(db.String(255))
    puw_sow_rotw = db.Column(db.String(255))
    total_drilling_time = db.Column(db.String(255))
    ton_miles = db.Column(db.String(255))

# AFE Model
class AFE(db.Model):
    __tablename__ = "afe"

    profile_id = db.Column(db.Integer, db.ForeignKey("profile.id"), primary_key=True)
    afe_number_afe_cost = db.Column(db.String(256))
    daily_cost = db.Column(db.String(256))
    percent_afe_cumulative_cost = db.Column(db.String(256))
    daily_mud_cost = db.Column(db.String(256))
    cumulative_mud_cost = db.Column(db.String(256))

# Personnel In Charge Model
class PersonnelInCharge(db.Model):
    __tablename__ = "personnel_in_charge"

    profile_id = db.Column(db.Integer, db.ForeignKey("profile.id"), primary_key=True)
    day_night_drilling_supv = db.Column(db.String(256))
    drilling_superintendent = db.Column(db.String(256))
    rig_superintendent = db.Column(db.String(256))
    drilling_engineer = db.Column(db.String(256))
    hse_supervisor = db.Column(db.String(256))

# Summary Model
class Summary(db.Model):
    __tablename__ = "summary"

    profile_id = db.Column(db.Integer, db.ForeignKey("profile.id"), primary_key=True)
    hours_24_summary = db.Column(db.Text)
    hours_24_forecast = db.Column(db.Text)
    status = db.Column(db.Text)

# Time Breakdown Model
class TimeBreakdown(db.Model):
    __tablename__ = "time_breakdown"

    profile_id = db.Column(db.Integer, db.ForeignKey("profile.id"), primary_key=True)
    start = db.Column(db.String(256), primary_key=True)
    end = db.Column(db.String(256))
    elapsed = db.Column(db.Float)
    depth = db.Column(db.Float)
    pt_npt = db.Column(db.String(256))
    code = db.Column(db.String(256))
    description = db.Column(db.Text)
    operation = db.Column(db.Text)

# Helper Function for JSON Serialization
def serialize_model(model):
    """
    Dynamically serialize a SQLAlchemy model instance into a dictionary.
    """
    return {column.key: getattr(model, column.key) for column in model.__table__.columns}

# Database Initialization Function
def init_db(app):
    """
    Initialize the database with the Flask app.
    """
    db.init_app(app)
    with app.app_context():
        db.create_all()