from flask import Blueprint, current_app, jsonify, request, send_file, send_from_directory, make_response, redirect, url_for, flash, render_template
from werkzeug.utils import secure_filename
import pandas as pd
from app import db
from app.models import City, Address, Submission
from app.forms import SubmissionForm, UploadForm
import qrcode
import os
import io
from fpdf import FPDF
import xlsxwriter
import logging
bp = Blueprint('main', __name__)
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def ensure_directory_exists(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)
        logger.info(f"Created directory: {directory}")

def save_file(form_file, folder):
    filename = secure_filename(form_file.filename)
    file_path = os.path.join(folder, filename)
    form_file.save(file_path)
    logger.info(f"Saved file: {file_path}")
    return file_path

def generate_qr_code(data, filename):
    qr_codes_dir = os.path.join(current_app.root_path, 'static', 'qr_codes')
    ensure_directory_exists(qr_codes_dir)
    img = qrcode.make(data)
    img_path = os.path.join(qr_codes_dir, filename)
    img.save(img_path)
    logger.info(f"Generated QR code: {img_path}")
    return img_path  # Return just the filename, not the full path

def import_data(file_path, city_name):
    df = pd.read_excel(file_path, engine='openpyxl')
    df.fillna("Unknown", inplace=True)

    city = City.query.filter_by(name=city_name).first()
    if not city:
        city = City(name=city_name)
        db.session.add(city)
        db.session.commit()
        logger.info(f"Created new city: {city_name}")

    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.add_font('TWCenMT', '', '/app/static/fonts/TwCenMT.TTF', uni=True)

    pdf.set_font('TWCenMT', '', 12)

    for index, row in df.iterrows():
        address = row['Address']
        owner_name = row['Owner']
        
        unique_token = os.urandom(8).hex()
        
        # Use url_for to dynamically generate the URL
        url = url_for('main.property', unique_token=unique_token, _external=True)

        qr_filename = f'{unique_token}.png'
        qr_code_path = generate_qr_code(url, qr_filename)

        new_address = Address(
            city_id=city.id, 
            address=address, 
            owner_name=owner_name, 
            unique_token=unique_token, 
            qr_code_path=qr_code_path
        )
        db.session.add(new_address)

        output_pdf_path = os.path.join(current_app.root_path, 'static', 'pdfs', f'{unique_token}_mailing_slip.pdf')
        generate_mailing_slip_pdf(pdf, address, url, qr_code_path, os.path.join(current_app.root_path, 'static', 'pdfs', 'LSIPPDF.png'))

    db.session.commit()
    logger.info(f"Imported data for city: {city_name}")

@bp.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
        return jsonify({"filename": filename}), 200
    return jsonify({"error": "File not allowed"}), 400


@bp.route('/api/cities', methods=['GET'])
def get_cities():
    cities = City.query.all()
    city_names = [city.name for city in cities]
    return jsonify(city_names)

@bp.route('/api/addresses', methods=['GET'])
def get_addresses():
    city_name = request.args.get('city')
    city = City.query.filter_by(name=city_name).first()
    if city:
        addresses = Address.query.filter_by(city_id=city.id).all()
        address_list = [address.address for address in addresses]
        return jsonify(address_list)
    else:
        return jsonify([]), 404

@bp.route('/api/submit_property', methods=['POST'])
def submit_property():
    data = request.form
    primary_plumbing_photo = None
    secondary_plumbing_photo = None

    # Retrieve the address from the database using the provided address_id
    address_id = data['address_id']
    address = Address.query.get(address_id)

    if not address:
        return jsonify({"error": "Address not found"}), 404

    # Create directory for city if it doesn't exist
    city_name = address.city.name.replace(" ", "")
    address_str = address.address.replace(" ", "").replace(".", "").replace(",", "").replace("/", "")

    city_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], city_name)
    if not os.path.exists(city_folder):
        os.makedirs(city_folder)

    # Save primary plumbing photo
    if 'primary_plumbing_photo' in request.files:
        file = request.files['primary_plumbing_photo']
        if file and allowed_file(file.filename):
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = secure_filename(f"{address_str}_primary.{ext}")
            file_path = os.path.join(city_folder, filename)
            file.save(file_path)
            primary_plumbing_photo = os.path.join(city_name, filename)

    # Save secondary plumbing photo
    if 'secondary_plumbing_photo' in request.files:
        file = request.files['secondary_plumbing_photo']
        if file and allowed_file(file.filename):
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = secure_filename(f"{address_str}_secondary.{ext}")
            file_path = os.path.join(city_folder, filename)
            file.save(file_path)
            secondary_plumbing_photo = os.path.join(city_name, filename)

    # Create a new submission
    new_submission = Submission(
        address_id=address_id,
        plumbing_install_date=data['plumbing_install_date'],
        water_softener_usage=data['water_softener_usage'],
        primary_plumbing_type=data['primary_plumbing_type'],
        primary_plumbing_photo=primary_plumbing_photo,
        secondary_plumbing_type=data['secondary_plumbing_type'],
        secondary_plumbing_photo=secondary_plumbing_photo,
        comments=data.get('comments', '')
    )

    db.session.add(new_submission)
    db.session.commit()
    return jsonify({"message": "Submission successful"}), 200


@bp.route("/")
@bp.route("/home", methods=['GET', 'POST'])
def home():
    form = UploadForm()  # Assuming you are using the UploadForm here
    if form.validate_on_submit():
        city_name = form.city_name.data
        file_path = save_file(form.excel_file.data, current_app.config['UPLOAD_FOLDER'])
        try:
            import_data(file_path, city_name)
            flash('File successfully uploaded and data imported', 'success')
        except Exception as e:
            flash(f'Error importing data: {e}', 'danger')
        return redirect(url_for('main.admin'))  # Redirect to avoid form resubmission
    
    cities = City.query.all()  # Fetch cities to display
    return render_template('admin.html', form=form, cities=cities)
@bp.route("/admin", methods=['GET', 'POST'])
def admin():
    form = UploadForm()  # This is the form used in the template
    if form.validate_on_submit():
        city_name = form.city_name.data
        file_path = save_file(form.excel_file.data, current_app.config['UPLOAD_FOLDER'])
        try:
            import_data(file_path, city_name)
            flash('File successfully uploaded and data imported', 'success')
            logger.info(f"File uploaded and data imported for city: {city_name}")
        except Exception as e:
            flash(f'Error importing data: {e}', 'danger')
            logger.error(f"Error importing data: {e}")
        return redirect(url_for('main.admin'))
    
    cities = City.query.all()
    # Pass the form object here when rendering the template
    return render_template('admin.html', form=form, cities=cities)

@bp.route("/city/<string:city_name>")
def city_properties(city_name):
    city = City.query.filter_by(name=city_name).first_or_404()
    properties = Address.query.filter_by(city_id=city.id).all()
    return render_template('city.html', city=city, properties=properties)

@bp.route("/property/<string:unique_token>", methods=['GET', 'POST'])
def property(unique_token):
    address = Address.query.filter_by(unique_token=unique_token).first_or_404()
    form = SubmissionForm()
    
    if form.validate_on_submit():
        primary_plumbing_photo = None
        secondary_plumbing_photo = None

        city_name = address.city.name.replace(" ", "")
        address_str = address.address.replace(" ", "").replace(".", "").replace(",", "").replace("/", "")

        city_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], city_name)
        if not os.path.exists(city_folder):
            os.makedirs(city_folder)

        if form.primary_plumbing_photo.data:
            file = form.primary_plumbing_photo.data
            if file and allowed_file(file.filename):
                ext = file.filename.rsplit('.', 1)[1].lower()
                filename = secure_filename(f"{address_str}_primary.{ext}")
                file_path = os.path.join(city_folder, filename)
                file.save(file_path)
                primary_plumbing_photo = os.path.join(city_name, filename)

        if form.secondary_plumbing_photo.data:
            file = form.secondary_plumbing_photo.data
            if file and allowed_file(file.filename):
                ext = file.filename.rsplit('.', 1)[1].lower()
                filename = secure_filename(f"{address_str}_secondary.{ext}")
                file_path = os.path.join(city_folder, filename)
                file.save(file_path)
                secondary_plumbing_photo = os.path.join(city_name, filename)

        submission = Submission(
            address_id=address.id,
            plumbing_install_date=form.plumbing_install_date.data,
            water_softener_usage=form.water_softener_usage.data,
            primary_plumbing_type=form.primary_plumbing_type.data,
            primary_plumbing_photo=primary_plumbing_photo,
            secondary_plumbing_type=form.secondary_plumbing_type.data,
            secondary_plumbing_photo=secondary_plumbing_photo,
            comments=form.comments.data
        )

        db.session.add(submission)
        db.session.commit()
        flash('Your submission has been recorded!', 'success')
        logger.info(f"New submission recorded for address: {address.address}")
        return redirect(url_for('main.thank_you'))
    else:
        logger.debug(f"Form validation failed: {form.errors}")
    
    return render_template('property.html', form=form, address=address)

@bp.route("/thank_you")
def thank_you():
    return render_template('thank_you.html')

def save_picture(form_picture):
    random_hex = os.urandom(8).hex()
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(current_app.config['UPLOAD_FOLDER'], picture_fn)
    form_picture.save(picture_path)
    logger.info(f"Saved picture: {picture_path}")
    return picture_fn

@bp.route("/qr_codes/<filename>")
def qr_code(filename):
    return send_from_directory('static/qr_codes', filename)

@bp.route("/city/<string:city_name>/submissions")
def city_submissions(city_name):
    city = City.query.filter_by(name=city_name).first_or_404()
    sort_by = request.args.get('sort_by', 'plumbing_install_date')
    sort_order = request.args.get('sort_order', 'asc')
    filters = request.args.getlist('filter')

    query = Submission.query.join(Address).filter(Address.city_id == city.id)

    if sort_order == 'desc':
        query = query.order_by(db.desc(getattr(Submission, sort_by)))
    else:
        query = query.order_by(getattr(Submission, sort_by))

    submissions = query.all()

    return render_template('city_submissions.html', city=city, submissions=submissions, sort_by=sort_by, sort_order=sort_order, filters=filters)

@bp.route("/export_city_data/<string:city_name>")
def export_city_data(city_name):
    city = City.query.filter_by(name=city_name).first_or_404()
    addresses = Address.query.filter_by(city_id=city.id).all()
    
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet()

    worksheet.write(0, 0, 'Address')
    worksheet.write(0, 1, 'Owner Name')
    worksheet.write(0, 2, 'Plumbing Install Date')
    worksheet.write(0, 3, 'Water Softener Usage')
    worksheet.write(0, 4, 'Primary Plumbing Type')
    worksheet.write(0, 5, 'Primary Plumbing Photo')
    worksheet.write(0, 6, 'Secondary Plumbing Type')
    worksheet.write(0, 7, 'Secondary Plumbing Photo')

    row = 1
    for address in addresses:
        submissions = Submission.query.filter_by(address_id=address.id).all()
        for submission in submissions:
            worksheet.write(row, 0, address.address)
            worksheet.write(row, 1, address.owner_name)
            worksheet.write(row, 2, submission.plumbing_install_date)
            worksheet.write(row, 3, submission.water_softener_usage)
            worksheet.write(row, 4, submission.primary_plumbing_type)
            worksheet.write(row, 5, submission.primary_plumbing_photo)
            worksheet.write(row, 6, submission.secondary_plumbing_type)
            worksheet.write(row, 7, submission.secondary_plumbing_photo)
            row += 1

    workbook.close()
    output.seek(0)
    logger.info(f"Exported city data for {city_name}")

    return send_file(output, download_name=f'{city_name}_data.xlsx', as_attachment=True)

def generate_mailing_slip_pdf(pdf, address, url, qr_code_path, template_path):
    # Check if the QR code exists (full path should already be passed)
    if not os.path.exists(qr_code_path):
        raise FileNotFoundError(f"QR code image not found: {qr_code_path}")

    # Check if the template exists
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Template image not found: {template_path}")

    # Add a new page for the current address
    pdf.add_page()

    # Set TW Cen MT Font (assuming the ttf file is already added to FPDF)
    pdf.set_font('TwCenMT', '', 18)

    # Add the template as a background
    pdf.image(template_path, x=0, y=0, w=210, h=297)  # Adjust to match the template

    # Add recipient name ("Resident")
    pdf.set_xy(40, 50)
    pdf.cell(200, 10, txt="Resident", ln=True)

    # Add address on the next line
    pdf.set_xy(40, 58)  # Adjust the y-position as needed
    pdf.cell(200, 10, txt=f"{address}", ln=True)

    # Add city, state, and zip (replace with actual city, state, zip)
    pdf.set_xy(40, 65)
    pdf.cell(200, 10, txt="Drexel, MO 64742", ln=True)

    # Add the URL
    pdf.set_xy(25, 130)
    pdf.cell(200, 10, txt=f"{url}", ln=True)

    # Add the QR code
    pdf.image(qr_code_path, x=55, y=140, w=100)  # Ensure the correct path format for Linux

@bp.route("/export_mailing_slips/<string:city_name>")
def export_mailing_slips(city_name):
    city = City.query.filter_by(name=city_name).first_or_404()
    addresses = Address.query.filter_by(city_id=city.id).all()

    # Path for the combined PDF
    output_pdf_path = os.path.join(current_app.root_path, 'static', 'pdfs', f'{city_name}_mailing_slips.pdf')
    template_pdf_path = os.path.join(current_app.root_path, 'static', 'pdfs', 'LSIPPDF.png')

    ensure_directory_exists(os.path.dirname(output_pdf_path))

    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.add_font('TWCenMT', '', os.path.join(current_app.root_path, 'static', 'fonts', 'TwCenMT.TTF'), uni=True)
    pdf.set_font('TWCenMT', '', 12)

    for address in addresses:
        url = f'https://qr-mailer.trekk.design/property/{address.unique_token}'
        #url = f'https://127.0.0.1:5000/property/{address.unique_token}'
        # Only use the filename here, not any directories
        qr_code_filename = os.path.basename(address.qr_code_path)

        # Correctly rebuild the full path
        qr_code_full_path = os.path.join(current_app.root_path, 'static', 'qr_codes', qr_code_filename).replace("\\", "/")

        # Generate the mailing slip for each address
        generate_mailing_slip_pdf(pdf, address.address, url, qr_code_full_path, template_pdf_path)

    pdf.output(output_pdf_path)

    if os.path.exists(output_pdf_path):
        return send_file(output_pdf_path, as_attachment=True)
    else:
        return jsonify({"error": "PDF generation failed"}), 500

def delete_file(file_path):
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Deleted file: {file_path}")
        else:
            logger.warning(f"File not found: {file_path}")
    except Exception as e:
        logger.error(f"Error deleting file {file_path}: {e}")

@bp.route("/delete_city", methods=['GET'])
def delete_city():
    city_name = request.args.get('city_name')
    try:
        city = City.query.filter_by(name=city_name).first_or_404()
        addresses = Address.query.filter_by(city_id=city.id).all()

        for address in addresses:
            submissions = Submission.query.filter_by(address_id=address.id).all()
            for submission in submissions:
                # Delete any plumbing photos associated with the submissions
                if submission.primary_plumbing_photo:
                    delete_file(os.path.join(current_app.config['UPLOAD_FOLDER'], submission.primary_plumbing_photo))
                if submission.secondary_plumbing_photo:
                    delete_file(os.path.join(current_app.config['UPLOAD_FOLDER'], submission.secondary_plumbing_photo))
                db.session.delete(submission)

            # Construct the absolute path for the QR code
            qr_code_abs_path = os.path.join(current_app.root_path, 'static', 'qr_codes', os.path.basename(address.qr_code_path))
            delete_file(qr_code_abs_path)

            db.session.delete(address)

        # Delete the generated PDF for mailing slips
        delete_file(os.path.join(current_app.root_path, 'static', 'pdfs', f'{city_name}_mailing_slips.pdf'))

        db.session.delete(city)
        db.session.commit()
        flash(f'City "{city_name}" and all associated data have been deleted.', 'success')
        logger.info(f'City "{city_name}" deleted.')

    except Exception as e:
        flash(f'Error deleting city: {e}', 'danger')
        logger.error(f"Error deleting city: {e}")
    
    return redirect(url_for('main.admin'))

