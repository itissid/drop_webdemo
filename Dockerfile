# Use an official Python runtime as a base image
FROM python:3.9-slim-buster

ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install poetry
RUN pip install poetry

# Arguments to determine if projects should be installed from GitHub
ARG INSTALL_DROP_BACKEND_FROM_GITHUB=false
ARG INSTALL_HERENOW_FROM_GITHUB=false
ARG REPO_DROP_BACKEND_URL=https://github.com/itissid/drop_PoT.git
ARG REPO_B_URL=https://github.com/itissid/projectB.git

# Copy local projects to container
COPY ./path_to_projectA_on_host /app/projectA
COPY ./path_to_projectB_on_host /app/projectB

# Install Project B
RUN if [ "$INSTALL_B_FROM_GITHUB" = "true" ]; then \
        git clone $REPO_B_URL /app/projectB && \
        cd /app/projectB && \
        poetry install; \
    else \
        cd /app/projectB && \
        poetry install; \
    fi

# Install Project A
RUN if [ "$INSTALL_A_FROM_GITHUB" = "true" ]; then \
        git clone $REPO_A_URL /app/projectA && \
        cd /app/projectA && \
        poetry install; \
    else \
        cd /app/projectA && \
        poetry install; \
    fi

# Expose the port the app runs on
EXPOSE 8000

# Set the command to run your application
CMD ["uvicorn", "projectA.main:app", "--host", "0.0.0.0", "--port", "8000"]
