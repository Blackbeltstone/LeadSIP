# Use the official Python image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Ensure the upload and static folders exist with the correct permissions
RUN mkdir -p /app/static/uploads

# Correctly copy the static files into the container
COPY ./app/static /app/static

# Expose port 5000 for Flask
EXPOSE 5000

# Set environment variables
ENV FLASK_APP=run.py
ENV FLASK_ENV=development

# Do not hardcode secrets in Dockerfile
# ENV SECRET_KEY=your_secret_key

# Command to run the Flask app
CMD ["flask", "run", "--host=0.0.0.0"]
