/**
 * Cypress configuration file
 *
 * - baseUrl: set to localhost:5000 where the Flask app runs
 * - e2e: configuration for end-to-end tests
 * - video: disabled for faster test runs
 * - screenshotOnRunFailure: enabled to capture failures
 */

const { defineConfig } = require('cypress');

module.exports = defineConfig({
  baseUrl: 'http://localhost:5000',
  video: false,
  screenshotOnRunFailure: true,
  e2e: {
    setupNodeEvents(on, config) {
      // implement node event listeners here
    },
    specPattern: 'cypress/e2e/**/*.cy.js',
  },
});
