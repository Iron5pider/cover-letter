import re
import pdfplumber


def get_job_title(text):
    # Regex to find the job title after a date and strip out any irrelevant parts
    job_title_match = re.search(
        r'\d{1,2}/\d{1,2}/\d{2}, \d{1,2}:\d{2} [APM]{2} (.*?)\|', text
    )

    if job_title_match:
        # Extract the potential job title
        job_title = job_title_match.group(1).strip()

        # Further refine to remove any unwanted text like "Arizona State University"
        job_title = re.sub(r'Arizona State University', '', job_title, flags=re.IGNORECASE).strip()

        return job_title if job_title else "Job Title Not Found"
    else:
        return "Job Title Not Found"


# Function to extract department name and format it for the receiver's address
def get_department_name(text):
    department_match = re.search(
        r'Department Name\s*Full-Time/Part-Time\s*\n\s*(.*?)\s*\n', text, re.IGNORECASE)

    department_name = department_match.group(1).strip() if department_match else "Department Name Not Found"
    department_name = department_name.strip('Part-Time')
    return department_name


def get_desired_qualifications(text):
    qualifications_section = ""
    capture = False
    for line in text.splitlines():
        if re.search(r'Desired Qualifications', line, re.IGNORECASE):
            capture = True
            continue
        elif re.search(r'Working Environment', line, re.IGNORECASE):
            break
        elif capture:
            qualifications_section += line.strip() + "\n"

    if qualifications_section:
        # Split the text into individual qualifications
        qualifications_lines = [q.strip() for q in qualifications_section.split('\n') if q.strip()]
        # Format the output by bullet points, joining split lines
        formatted_qualifications = []
        current_qualification = ""
        for line in qualifications_lines:
            if line.startswith('•'):
                if current_qualification:
                    formatted_qualifications.append(current_qualification)
                current_qualification = line
            else:
                current_qualification += ' ' + line
        if current_qualification:
            formatted_qualifications.append(current_qualification)
        return "\n".join(formatted_qualifications)
    else:
        return "Desired Qualifications Not Found"


def extract_essential_duties(text):
    duties_section = ""
    capture = False

    # Capture the essential duties section
    for line in text.splitlines():
        if re.search(r'Essential Duties', line, re.IGNORECASE):
            capture = True
            continue
        elif re.search(r'Minimum Qualifications', line, re.IGNORECASE):
            break
        elif capture:
            duties_section += line.strip() + "\n"


    if duties_section:
        # Remove unwanted text patterns while preserving relevant information
        # 1. Remove URLs
        duties_section = re.sub(r'http\S+|www\.\S+', '', duties_section)
        # 2. Remove any timestamps or irrelevant dates
        duties_section = re.sub(r'\d{1,2}/\d{1,2}/\d{2}, \d{1,2}:\d{2} [APM]{2}', '', duties_section)
        # 3. Remove specific unwanted text like "Arizona State University"
        duties_section = re.sub(r'\bArizona State University\b', '', duties_section, flags=re.IGNORECASE)
        # 4. Remove job titles and unwanted patterns such as "Lead Research Aide (FWS Eligible) |"
        duties_section = re.sub(r'\bLead Research Aide \(FWS Eligible\) \|', '', duties_section, flags=re.IGNORECASE)
        # 5. Remove "1/ " pattern
        duties_section = re.sub(r'\b1/ ', '', duties_section)
        # 6. Clean up any excessive whitespace or stray punctuation left after removal
        duties_section = re.sub(r'\s{2,}', ' ', duties_section).strip()

        # Split the text into individual duties
        duties_lines = [d.strip() for d in duties_section.split('\n') if d.strip()]

        # Join the cleaned-up duties back together
        return "\n".join(duties_lines)
    else:
        return "Essential Duties Not Found"
def extract_information_from_pdf(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        text = ''
        for page in pdf.pages:
            text += page.extract_text()
    # print(text)
    job_title = get_job_title(text)
    department_name = get_department_name(text)
    desired_qualifications = get_desired_qualifications(text)
    essential_duties = extract_essential_duties(text)

    return job_title, department_name, desired_qualifications, essential_duties
