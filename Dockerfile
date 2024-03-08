
# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Poetry and Requirements
RUN pip install poetry
COPY pyproject.toml poetry.lock .
# Because Poetry sometimes has issues with Docker, we revert back to PIP
RUN poetry export -f requirements.txt --output requirements.txt
RUN pip install -r requirements.txt


# Install Java (required for Tabula)
RUN apt-get update && \
    apt-get install -y default-jre

# Install Tabula
RUN pip install tabula-py


# Run app.py when the container launches
CMD ["python", "run.py"]