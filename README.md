# Cover Letter Pro

Cover Letter Pro is a Flask-based web application that helps users generate professional cover letters using OpenAI's language model. It allows users to upload job descriptions and automatically creates tailored cover letters based on the user's profile and the job requirements.

## Features

- User authentication (register, login, logout)
- User profile management
- Job description upload (supports PDF, DOC, DOCX, and TXT files)
- Automatic cover letter generation using OpenAI's API
- Cover letter management (view, download, delete)
- Responsive design for various screen sizes

## Prerequisites

- Python 3.7+
- Flask
- SQLAlchemy
- OpenAI Python library
- Other dependencies (see `requirements.txt`)

## Setup

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/cover-letter-pro.git
   cd cover-letter-pro
   ```

2. Create a virtual environment and activate it:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

4. Set up your OpenAI API key:
   - Create a `.env` file in the project root
   - Add your OpenAI API key: `OPENAI_API_KEY=your_api_key_here`

5. Initialize the database:
   ```
   flask db init
   flask db migrate
   flask db upgrade
   ```

6. Run the application:
   ```
   flask run
   ```

7. Open a web browser and navigate to `http://localhost:5000`

## Usage

1. Register for an account or log in if you already have one.
2. Complete your profile information.
3. On the home page, upload a job description file (PDF, DOC, DOCX, or TXT).
4. Click "Generate Cover Letters" to create a cover letter based on the job description and your profile.
5. View, download, or delete your generated cover letters from the "My Cover Letters" page.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgements

- OpenAI for providing the API used in generating cover letters
- Flask and its extensions for the web framework
- Bootstrap for the frontend design