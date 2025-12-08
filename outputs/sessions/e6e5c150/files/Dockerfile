# Use a slim Python base image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED 1
ENV APP_HOME /app
WORKDIR $APP_HOME

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . $APP_HOME

# Expose the port FastAPI runs on
EXPOSE 8000

# Command to run the application using Uvicorn
# Use gunicorn with uvicorn workers for production stability
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]