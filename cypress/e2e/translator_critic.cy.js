/**
 * Cypress end-to-end tests for AI Translator & Critic
 *
 * This file contains two tests:
 * 1) Successful translation and evaluation flow using mock mode (no network calls).
 * 2) Error-handling flow where the external API returns 500 (when using auth mode).
 *
 * Key improvements for reliability:
 * - Uses element IDs (#btn_translate, #btn_judge) for reliable button selection
 * - Mock mode is tested, which returns local responses without calling external API
 * - Error test uses auth mode to trigger network call and validates error handling
 *
 * Installation (project root):
 *   npm install cypress --save-dev
 *
 * Running in Codespaces / headless:
 *   npx cypress run --spec "cypress/e2e/translator_critic.cy.js"
 *
 * Opening interactive runner (desktop):
 *   npx cypress open
 *
 * Notes about mocking and asynchrony:
 * - Mock mode returns local responses immediately, so cy.wait() on network intercepts is not needed
 * - Auth mode attempts to call the real API, allowing us to test error handling with cy.intercept()
 * - Element IDs make selectors stable and less fragile than text-based matching
 */

const MENTORPIECE_URL = 'https://api.mentorpiece.org/v1/process-ai-request'

describe('AI Translator & Critic - UI tests with mocked API', () => {

  beforeEach(() => {
    // Start each test from the app root. Adjust baseUrl in cypress config if needed.
    cy.visit('/');
  });

  it('Successful translation and evaluation (mocked responses)', () => {
    // Ensure mock mode is selected in the UI (default is mock, but we set it explicitly).
    // This radio input was added to the form with id `mode_mock`.
    cy.get('#mode_mock').check();
    cy.get('#mode_mock').should('be.checked');

    // Type the source text into textarea (id `source_text` in the template)
    cy.get('#source_text').clear().type('Солнце светит.');

    // Select the target language. Now using Russian language names from the select.
    cy.get('#target_lang').select('Английский');

    // Click the Translate button by ID
    cy.get('#btn_translate').click();

    // Verify mock mode is active and the mocked translation appears in the UI.
    // Mock mode returns local responses, so we don't wait on network calls.
    cy.contains('Mocked Translation: The sun is shining.').should('be.visible');

    // Click the Judge button by ID
    cy.get('#btn_judge').click();

    // Verify the mocked grade text appears in the evaluation block
    cy.contains('Mocked Grade: 9/10. Fluent and accurate.').should('be.visible');
  });


  it('API failure handling: external API returns 500 and UI shows error', () => {
    // For error handling test, select 'auth' mode so the app will attempt
    // to call the external API. We mock the endpoint to return a 500 error.
    cy.get('#mode_auth').check();
    cy.intercept('POST', MENTORPIECE_URL, {
      statusCode: 500,
      body: { response: 'Internal Server Error' }
    }).as('apiFail');

    // Fill form and submit
    cy.get('#source_text').clear().type('Солнце светит.');
    cy.get('#target_lang').select('Английский');
    cy.get('#btn_translate').click();

    // Wait for the failed API request to occur.
    cy.wait('@apiFail');

    // The app's call_llm returns a human-readable error string which is shown
    // in the evaluation area. In auth mode without a valid API key, it will
    // show the missing key error or a network error.
    cy.contains(/Network\/HTTP error|Error: MENTORPIECE_API_KEY|error/i).should('be.visible');
  });

});
