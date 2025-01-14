# Python file to run flask and render HTML templates for the web-app. 
# Used Python loggging module, OpenTelemetry for tracing and Jaeger for exporting traces.
# The app has 4 routes: index, course_catalog, course_details and add_course.

# Imports
import json
import os
import logging

from flask import Flask, render_template, request, redirect, url_for, flash

import opentelemetry.trace as trace
from opentelemetry.trace import SpanKind
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor


# Flask App Initialization
app = Flask(__name__)
app.secret_key = 'secret' 
COURSE_FILE = './new/CS203_Lab_01/course_catalog.json'


# OpenTelemetry Setup
resource = Resource.create({"service.name": "course-catalog-service"})
trace.set_tracer_provider(TracerProvider(resource=resource))
tracer = trace.get_tracer(__name__)


# Jaeger Exporter
j_e = JaegerExporter(
    agent_host_name="localhost",
    agent_port=9411,
)


# Span Processing
s_p = BatchSpanProcessor(j_e)
trace.get_tracer_provider().add_span_processor(s_p)


# Flask Instrumentation
FlaskInstrumentor().instrument_app(app)


# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] - %(message)s",
    handlers=[logging.StreamHandler()]
    )


# Utility Functions
# Function to load courses from the JSON file.
def load_courses():
    if not os.path.exists(COURSE_FILE):
        return []
    with open(COURSE_FILE, 'r') as file:
        return json.load(file)

# Function to save new course data to the JSON file.
def save_courses(data):
    """Save new course data to the JSON file."""
    courses = load_courses()  # Load existing courses
    courses.append(data)  # Append the new course
    with open(COURSE_FILE, 'w') as file:
        json.dump(courses, file, indent=4)


# Routes
# Index Page
@app.route('/')
def index():
    # Trace the user's IP, URL and HTTP method.
    with tracer.start_as_current_span("index", kind=SpanKind.CLIENT) as span:

        span.set_attribute("user_ip", request.remote_addr)
        span.set_attribute("http_url", request.url)
        span.set_attribute("http_method", request.method)   

        span.add_event("Index Page")

    # Console Log
    logging.info("Index Page")

    # Render the index.html template.
    return render_template('index.html')


# Course Catalog Page
@app.route('/catalog')
def course_catalog():

    # Load courses from the JSON file.
    courses = load_courses()

    # Trace the user's IP, URL and HTTP method.
    with tracer.start_as_current_span("index", kind=SpanKind.CLIENT) as span:

        span.set_attribute("user_ip", request.remote_addr)
        span.set_attribute("http_url", request.url)
        span.set_attribute("http_method", request.method)   
        span.set_attribute("course_count", len(courses))

        span.add_event("Course Catalog Page")

    # Console Log
    logging.info("Course Catalog Page")

    # Render the course_catalog.html template.
    return render_template('course_catalog.html', courses=courses)


# Course Details Page - Dynamic Route based on given course code.
@app.route('/course/<code>')
def course_details(code):

    # Load courses from the JSON file.
    courses = load_courses()

    # Find the course with the given code.
    course = next((course for course in courses if course['code'] == code), None)

    # Trace the user's IP, URL and HTTP method.
    with tracer.start_as_current_span("index", kind=SpanKind.CLIENT) as span:

        span.set_attribute("user_ip", request.remote_addr)
        span.set_attribute("http_url", request.url)
        span.set_attribute("http_method", request.method)   

        # If no course found with the given code, log an error.
        if not course:
            span.set_attribute("error.message", f"No course found with code '{code}'.")
            flash(f"No course found with code '{code}'.", "error")
            logging.error(f"No course found with code '{code}'.")
            return redirect(url_for('course_catalog'))

        # If course found, log the course code.
        span.set_attribute("course_code", course['code'])
        logging.info(f"Course Details Page: {course['code']}")
    
    # Render the course_details.html template.
    return render_template('course_details.html', course=course)


# Add Course Option
@app.route('/add_course', methods=['GET', 'POST'])
def add_course():

    # Trace the user's IP, URL and HTTP method.
    with tracer.start_as_current_span("index", kind=SpanKind.CLIENT) as span:

        span.set_attribute("user_ip", request.remote_addr)
        span.set_attribute("http_url", request.url)
        span.set_attribute("http_method", request.method)   

        span.add_event("Add Course Page")
        logging.info("Add Course Page")

        # If the form is submitted, save the course data to the JSON file after checking for missing fields.
        if request.method == 'POST':
            course = {
                'code': request.form['code'],
                'name': request.form['name'],
                'instructor': request.form['instructor'],
                'semester': request.form['semester'],
                'schedule': request.form['schedule'],
                'classroom': request.form['classroom'],
                'prerequisites': request.form['prerequisites'],
                'grading': request.form['grading'],
                'description': request.form['description']
            }

            # Check for missing fields.
            missing_fields = [field for field, value in course.items() if not value and field!="description"]

            if missing_fields:
                
                # If missing fields, log an error and flash an error message.
                error_m = "Missing fields: " + ', '.join(missing_fields)
                span.set_status("error")
                span.add_event(error_m)
                flash(error_m, "error") 
                logging.error(error_m)
                return redirect(url_for('add_course'))

            # Save the course data to the JSON file.
            save_courses(course)
            span.add_event(f"Course '{course['name']}' added successfully!")
            logging.info(f"Course '{course['code']}' added successfully!")
            flash(f"Course '{course['code']}' added successfully!", "success")
            
            # Redirect to the course catalog page.
            return redirect(url_for('course_catalog'))
        
    # Render the add_course.html template.
    return render_template('add_course.html')

if __name__ == '__main__':
    app.run(debug=True)