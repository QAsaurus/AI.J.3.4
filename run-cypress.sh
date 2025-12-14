#!/bin/bash
#
# Script to run Cypress tests locally or in CI
# This attempts to run Cypress with or without a display server.
#
# Usage:
#   ./run-cypress.sh
#
# Requirements:
#   - Node.js 18+ installed
#   - npm packages installed (npm install)
#   - Flask app running on http://localhost:5000 (python src/app.py)

set -e

echo "================================"
echo "Running AI Translator & Critic E2E Tests"
echo "================================"

# Check if app is running
echo "Checking if Flask app is running on localhost:5000..."
if curl -s http://localhost:5000/ > /dev/null; then
    echo "✓ Flask app is accessible"
else
    echo "✗ Flask app not found on localhost:5000"
    echo "  Please start the app with: cd src && python app.py"
    exit 1
fi

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "Installing npm dependencies..."
    npm install
fi

echo ""
echo "Running Cypress tests in headless mode..."
echo ""

# Try to run with Xvfb if available, otherwise use electron renderer
if command -v xvfb-run &> /dev/null; then
    xvfb-run -a npx cypress run --spec "cypress/e2e/translator_critic.cy.js"
else
    echo "Note: Xvfb not available. Using electron browser without display server."
    npx cypress run --spec "cypress/e2e/translator_critic.cy.js" --browser electron 2>&1 || \
    npx cypress run --spec "cypress/e2e/translator_critic.cy.js"
fi

echo ""
echo "✓ Tests completed!"
