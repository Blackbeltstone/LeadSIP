from app import db
import uuid
import logging

# Initialize logging
logger = logging.getLogger(__name__)

class City(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    date_created = db.Column(db.DateTime, default=db.func.current_timestamp())

    def __repr__(self):
        return f"<City {self.name}>"

class Address(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    city_id = db.Column(db.Integer, db.ForeignKey('city.id'), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    owner_name = db.Column(db.String(100), nullable=False)
    unique_token = db.Column(db.String(16), unique=True, nullable=False, default=lambda: uuid.uuid4().hex[:16])
    qr_code_path = db.Column(db.String(200), nullable=False)
    city = db.relationship('City', backref=db.backref('addresses', lazy=True))

    def __repr__(self):
        return f"<Address {self.address}>"

class Submission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    address_id = db.Column(db.Integer, db.ForeignKey('address.id'), nullable=False)
    plumbing_install_date = db.Column(db.String(100), nullable=True)
    water_softener_usage = db.Column(db.String(100), nullable=True)
    primary_plumbing_type = db.Column(db.String(100), nullable=False)
    primary_plumbing_photo = db.Column(db.String(100), nullable=False)
    secondary_plumbing_type = db.Column(db.String(100), nullable=True)
    secondary_plumbing_photo = db.Column(db.String(100), nullable=True)
    comments = db.Column(db.Text, nullable=True)
    date_created = db.Column(db.DateTime, default=db.func.current_timestamp())
    address = db.relationship('Address', backref=db.backref('submissions', lazy=True))

    def __repr__(self):
        return f"<Submission {self.id} for address {self.address_id}>"
