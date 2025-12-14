# Devcontainer Dockerfile for Codespaces: Python + Node + Xvfb for Cypress GUI
FROM python:3.12-slim-bookworm

# Install system dependencies required for Cypress interactive mode and Python
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    xvfb \
    libgtk-3-0 \
    libgbm1 \
    libnotify4 \
    libnss3 \
    libxss1 \
    libasound2 \
    libxtst6 \
    libxkbfile1 \
    xauth \
    ca-certificates \
    curl \
    gnupg \
    git \
    wget \
    build-essential \
  && rm -rf /var/lib/apt/lists/*

# Install Node.js 20 (required for Cypress)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
  && apt-get install -y --no-install-recommends nodejs \
  && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /workspaces/AI.J.3.4

# Keep container small and clean
RUN npm --version || true

# Note: After adding this Dockerfile, rebuild the Codespace container (Command Palette -> Rebuild Container)
