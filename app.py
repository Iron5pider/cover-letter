from flask import Flask, render_template, request, send_file, flash, redirect, url_for, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from datetime import datetime
import time
import logging
import json
from fpdf import FPDF
from util import extract_information_from_pdf  # Import the function from util.py
from openai import OpenAI, OpenAIError  # Make sure to have the OpenAI library installed and configured
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')  # Use environment variable
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'docx'}
JOB_FOLDER = 'jobs'
OUTPUT_FOLDER = 'generated'
USER_DATA_FILE = 'user_data.json'  # File to store user information
COVER_LETTERS_FILE = 'cover_letters.json'  # File to store cover letter information
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max-limit

# OpenAI Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
ASSISTANT_ID = os.getenv('ASSISTANT_ID')
THREAD_ID = os.getenv('THREAD_ID')

if not OPENAI_API_KEY:
    raise ValueError("No OpenAI API key found. Please set the OPENAI_API_KEY environment variable.")

try:
    client = OpenAI(api_key=OPENAI_API_KEY)
except OpenAIError as e:
    logging.error(f"Failed to initialize OpenAI client: {e}")
    raise

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Ensure necessary directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(JOB_FOLDER, exist_ok=True)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    address = db.Column(db.String(200))
    phone = db.Column(db.String(20))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        flash('Invalid email or password', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('register.html')
        
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered', 'danger')
            return render_template('register.html')
        
        # Use 'pbkdf2:sha256' method instead of 'sha256'
        new_user = User(name=name, email=email, password=generate_password_hash(password, method='pbkdf2:sha256'))
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        current_user.name = request.form.get('name')
        current_user.address = request.form.get('address')
        current_user.phone = request.form.get('phone')
        db.session.commit()
        flash('Profile updated successfully', 'success')
    return render_template('profile.html')

def load_user_data():
    """Loads user data from a JSON file."""
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_user_data(user_data):
    """Saves user data to a JSON file."""
    with open(USER_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(user_data, f)


def load_cover_letters():
    """Loads cover letter data from a JSON file."""
    if os.path.exists(COVER_LETTERS_FILE):
        with open(COVER_LETTERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def save_cover_letters(cover_letters):
    """Saves cover letter data to a JSON file."""
    with open(COVER_LETTERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(cover_letters, f)


def allowed_file(filename):
    """Checks if the file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def wait_for_run_completion(thread_id, run_id, sleep_interval=5):
    """Waits for the OpenAI run to complete and returns the generated content."""
    while True:
        try:
            run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
            if run.completed_at:
                elapsed_time = run.completed_at - run.created_at
                formatted_elapsed_time = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
                logging.info(f"Run completed in {formatted_elapsed_time}")
                messages = client.beta.threads.messages.list(thread_id=thread_id)

                # Ensure UTF-8 encoding
                return messages.data[0].content[0].text.value
            elif run.failed_at:
                logging.error(f"Run failed: {run.last_error}")
                return None
        except Exception as e:
            logging.error(f"An error occurred while retrieving the run: {e}")
            return None
        logging.info("Waiting for run to complete...")
        time.sleep(sleep_interval)


def create_cover_letter_pdf(text_content, output_filename):
    """Creates a PDF file from the given text content."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", "", 11)

    # Split the content into lines
    lines = text_content.split('\n')

    for line in lines:
        pdf.multi_cell(0, 5, txt=line.encode('latin-1', errors='replace').decode('latin-1'))

    pdf.output(output_filename)
    logging.info(f"Created cover letter PDF: {output_filename}")


def generate_cover_letter(content_template, user_details, job_title, company_name):
    """Generates a cover letter with the correct format."""
    current_date = datetime.now().strftime("%B %d, %Y")
    
    header = (
        f"{user_details['name']}\n"
        f"{user_details['address']}\n"
        f"{user_details['city']}, {user_details['state']} {user_details['zip']}\n"
        f"{user_details['phone']}\n"
        f"{user_details['email']}\n\n"
        f"{current_date}\n\n"
        f"{company_name}\n"
        "Arizona State University\n"
        "Tempe, AZ\n\n"
        "Dear Hiring Manager,\n\n"
    )
    
    # Remove any existing header information and "Dear Hiring Manager," from the content
    content_without_header = content_template.split("Dear Hiring Manager,")[-1].strip()
    
    # Split the remaining content into paragraphs
    paragraphs = content_without_header.split('\n\n')
    
    # Remove any mentions of the company name or address from the paragraphs
    cleaned_paragraphs = []
    for paragraph in paragraphs:
        cleaned_paragraph = paragraph.replace(f"{company_name}\nArizona State University\nTempe, 85281", "").strip()
        if cleaned_paragraph:
            cleaned_paragraphs.append(cleaned_paragraph)
    
    # Combine the header with the formatted paragraphs
    formatted_content = header + '\n\n'.join(cleaned_paragraphs)
    
    # Add the closing
    formatted_content += f"\n\nWarm Regards,\n{user_details['name']}"
    
    return formatted_content


@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    """Handles the index route for user input and file uploads."""
    logger.debug("Index route accessed")
    user_data = load_user_data()

    if request.method == 'POST':
        # Retrieve user details from the form
        user_details = {
            'name': current_user.name,
            'address': current_user.address,
            'email': current_user.email,
            'phone': current_user.phone,
            'city': request.form.get('city', 'Tempe'),
            'state': request.form.get('state', 'AZ'),
            'zip': request.form.get('zip', '85281'),
            'company_address': request.form.get('company_address', 'Company Address')
        }

        # Handle job descriptions
        job_descriptions = request.files.getlist('job_description')
        generated_files = []
        uploaded_files = []  # New list to store uploaded file names

        for job_file in job_descriptions:
            if job_file and allowed_file(job_file.filename):
                uploaded_files.append(job_file.filename)  # Add filename to the list
                try:
                    job_path = os.path.join(JOB_FOLDER, secure_filename(job_file.filename))
                    job_file.save(job_path)
                    logging.info(f"Saved job file: {job_path}")

                    # Extract job details
                    job_title, department_name, desired_qualifications, essential_duties = extract_information_from_pdf(job_path)
                    logging.info(f"Extracted job details for: {job_title}")

                    # Construct message for OpenAI API
                    message_content = (
                        "Imagine you are an expert career coach helping a professional craft a compelling cover letter. "
                        f"Create a cover letter for the position of {job_title} "
                        "The cover letter must highlight the candidate's qualifications, skills, and experience, "
                        "aligning them with the desired qualifications and essential duties of the job as described below:\n\n"
                        f"Job Title: {job_title}\n"
                        f"Desired Qualifications:\n{desired_qualifications}\n"
                        f"Essential Duties:\n{essential_duties}\n\n"
                        "Use the applicant's background and skills from their resume to tailor the letter. "
                        "DO NOT Include placeholders for [Company Name], [Company Address], and [Company City, State Zip] in the letter."
                    )

                    try:
                        # OpenAI API calls
                        logging.info("Sending request to OpenAI API")
                        message = client.beta.threads.messages.create(
                            thread_id=THREAD_ID,
                            role="user",
                            content=message_content
                        )
                        run = client.beta.threads.runs.create(
                            thread_id=THREAD_ID,
                            assistant_id=ASSISTANT_ID,
                        )
                        cover_letter_template = wait_for_run_completion(THREAD_ID, run.id)
                        logging.info("Received response from OpenAI API")

                        if cover_letter_template:
                            cover_letter_content = generate_cover_letter(cover_letter_template, user_details, job_title, department_name)

                            # Save the cover letter files
                            text_filename = f"{secure_filename(job_title)}.txt"
                            pdf_filename = f"{secure_filename(job_title)}.pdf"
                            text_filepath = os.path.join(OUTPUT_FOLDER, text_filename)
                            pdf_filepath = os.path.join(OUTPUT_FOLDER, pdf_filename)

                            with open(text_filepath, 'w', encoding='utf-8') as f:
                                f.write(cover_letter_content)
                            
                            try:
                                create_cover_letter_pdf(cover_letter_content, pdf_filepath)
                            except Exception as pdf_error:
                                logging.error(f"Error creating PDF: {str(pdf_error)}")
                                flash(f"Error creating PDF: {str(pdf_error)}", 'danger')
                                # Continue with the process even if PDF creation fails

                            # Store cover letter information
                            cover_letters = load_cover_letters()
                            cover_letters.append({
                                'job_title': job_title,
                                'company_name': department_name,
                                'creation_date': datetime.now().strftime("%B %d, %Y"),
                                'text_file': text_filename,
                                'pdf_file': pdf_filename
                            })
                            save_cover_letters(cover_letters)

                            generated_files.append({'text': text_filename, 'pdf': pdf_filename})
                        else:
                            logging.error(f"Failed to generate cover letter for {job_title}")
                            flash(f"Failed to generate cover letter for {job_title}", 'danger')

                    except OpenAIError as e:
                        logging.error(f"OpenAI API error: {str(e)}")
                        flash(f"Error generating cover letter: {str(e)}", 'danger')
                    except Exception as e:
                        logging.error(f"Unexpected error during OpenAI API call: {str(e)}")
                        flash(f"Unexpected error generating cover letter: {str(e)}", 'danger')

                except Exception as e:
                    logging.error(f"Error processing job description file: {str(e)}")
                    flash(f"Error processing job description file: {str(e)}", 'danger')
            else:
                logging.warning(f"Invalid file type or no file uploaded for job description")
                flash(f"Invalid file type or no file uploaded for job description", 'danger')

        return render_template('result.html', generated_files=generated_files, user_data=user_data, uploaded_files=uploaded_files)

    return render_template('index.html', user_data=current_user)


@app.route('/cover_letters')
@login_required
def cover_letters():
    """Displays the user's generated cover letters with job title and date of creation."""
    cover_letters = load_cover_letters()
    user_data = load_user_data()
    return render_template('cover_letters.html', cover_letters=cover_letters, user_data=user_data)


@app.route('/preview/<filename>')
@login_required
def preview_file(filename):
    """Provides a preview of the generated text file."""
    text_filepath = os.path.join(OUTPUT_FOLDER, filename)
    user_data = load_user_data()
    if os.path.exists(text_filepath):
        with open(text_filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()

        cover_letters = load_cover_letters()
        department_name = None
        pdf_filename = None
        for letter in cover_letters:
            if letter['text_file'] == filename:
                department_name = letter.get('company_name', 'Department Name Not Found')
                pdf_filename = letter.get('pdf_file', filename.replace('.txt', '.pdf'))
                break

        return render_template('preview.html', content=content, filename=pdf_filename, user_data=user_data, department_name=department_name)
    else:
        flash('File not found for preview.', 'danger')
        return redirect(url_for('index'))


@app.route('/update/<filename>', methods=['GET', 'POST'])
@login_required
def update_cover_letter(filename):
    """Updates an existing cover letter."""
    text_filepath = os.path.join(OUTPUT_FOLDER, filename)
    user_data = load_user_data()
    if request.method == 'POST':
        new_content = request.form.get('content')
        with open(text_filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        flash('Cover letter updated successfully.', 'success')
        return redirect(url_for('cover_letters'))
    else:
        if os.path.exists(text_filepath):
            with open(text_filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            return render_template('update.html', content=content, filename=filename, user_data=user_data)
        else:
            flash('File not found for updating.', 'danger')
            return redirect(url_for('cover_letters'))


@app.route('/delete/<filename>', methods=['POST'])
@login_required
def delete_cover_letter(filename):
    """Deletes an existing cover letter."""
    text_filepath = os.path.join(OUTPUT_FOLDER, filename)
    pdf_filepath = text_filepath.replace('.txt', '.pdf')
    cover_letters = load_cover_letters()
    cover_letters = [letter for letter in cover_letters if letter['text_file'] != filename]
    save_cover_letters(cover_letters)
    try:
        if os.path.exists(text_filepath):
            os.remove(text_filepath)
        if os.path.exists(pdf_filepath):
            os.remove(pdf_filepath)
        flash('Cover letter deleted successfully.', 'success')
    except Exception as e:
        flash(f'Error deleting cover letter: {e}', 'danger')
    return redirect(url_for('cover_letters'))


@app.route('/download/<filename>')
@login_required
def download_file(filename):
    logging.info(f"Attempting to download file: {filename}")
    if not filename.lower().endswith('.pdf'):
        filename += '.pdf'
    
    pdf_filepath = os.path.join(OUTPUT_FOLDER, filename)
    logging.info(f"Full file path: {pdf_filepath}")

    if os.path.exists(pdf_filepath):
        logging.info(f"File found, sending: {pdf_filepath}")
        try:
            return send_file(
                pdf_filepath,
                as_attachment=True,
                download_name=filename,
                mimetype='application/pdf'
            )
        except Exception as e:
            logging.error(f"Error sending file: {str(e)}")
            flash(f'Error downloading file: {str(e)}', 'danger')
    else:
        logging.warning(f"File not found: {pdf_filepath}")
        flash('PDF file not found for download.', 'danger')
    
    return redirect(url_for('cover_letters'))


@app.route('/test')
def test():
    return "Server is running"

def init_db():
    with app.app_context():
        db.create_all()

if __name__ == '__main__':
    init_db()
    app.run(debug=True)