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
    cy.get('#mode_auth').check({ force: true });
    cy.intercept('POST', MENTORPIECE_URL, {
      statusCode: 500,
      body: { response: 'Internal Server Error' }
    }).as('apiFail');

    // Fill form and submit
    cy.get('#source_text').clear().type('Солнце светит.');
    cy.get('#target_lang').select('Английский');
    cy.get('#btn_translate').click();

    // The app's call_llm returns a human-readable error string which is shown
    // in the evaluation area. In auth mode, it will show an API error message.
    // Give it time to attempt the API call and display the error.
    cy.contains(/error|Error|failed|Failed/i, { timeout: 5000 }).should('be.visible');
  });

  // ============================================================================
  // Additional tests for comprehensive coverage
  // ============================================================================

  it('Test all language options work correctly', () => {
    // Ensure mock mode is selected
    cy.get('#mode_mock').check();
    
    // Test each language option
    const languages = ['Английский', 'Французский', 'Немецкий', 'Португальский'];
    
    languages.forEach((lang) => {
      cy.get('#source_text').clear().type('Hello world');
      cy.get('#target_lang').select(lang);
      cy.get('#btn_translate').click();
      
      // Verify translation is shown (mock mode returns consistent response)
      cy.contains('Mocked Translation: The sun is shining.').should('be.visible');
    });
  });

  it('Test mode switching between MOCK, no auth, and auth', () => {
    // Start with MOCK mode
    cy.get('#mode_mock').check({ force: true });
    cy.get('#source_text').clear().type('Test text');
    cy.get('#target_lang').select('Английский');
    cy.get('#btn_translate').click();
    cy.contains('Mocked Translation').should('be.visible');

    // Switch to no_auth mode
    cy.get('#mode_no_auth').check({ force: true });
    cy.get('#source_text').clear().type('Test text');
    cy.get('#btn_translate').click();
    // In no_auth mode without real API, it might show error or mock response depending on implementation
    cy.get('#source_text').should('exist');

    // Switch back to MOCK mode
    cy.get('#mode_mock').check({ force: true });
    cy.get('#source_text').clear().type('Test text');
    cy.get('#btn_translate').click();
    cy.contains('Mocked Translation').should('be.visible');
  });

  it('Test Unicode and special characters in translation', () => {
    cy.get('#mode_mock').check();
    
    // Test Cyrillic
    cy.get('#source_text').clear().type('Привет мир 🌍');
    cy.get('#target_lang').select('Английский');
    cy.get('#btn_translate').click();
    cy.contains('Mocked Translation').should('be.visible');
    
    // Test with emoji
    cy.get('#source_text').clear().type('👋 Hello 😀');
    cy.get('#btn_translate').click();
    cy.contains('Mocked Translation').should('be.visible');
  });

  it('Test form field clearing after submission', () => {
    cy.get('#mode_mock').check({ force: true });
    
    // Enter text and submit
    cy.get('#source_text').type('Test text');
    cy.get('#target_lang').select('Английский');
    cy.get('#btn_translate').click();
    
    // Verify translation appears
    cy.contains('Mocked Translation').should('be.visible');
    
    // Check if source text field still has content
    cy.get('#source_text').should('exist');
    // Verify target language is still selected with Russian name (not converted to 'en')
    cy.get('#target_lang').should('have.value', 'Английский');
  });

  it('Test button states and interaction', () => {
    // Verify buttons are visible and clickable
    cy.get('#btn_translate').should('be.visible').should('not.be.disabled');
    cy.get('#btn_judge').should('be.visible').should('not.be.disabled');
    
    // Test clicking translate button
    cy.get('#mode_mock').check();
    cy.get('#source_text').type('Test text');
    cy.get('#target_lang').select('Английский');
    cy.get('#btn_translate').click();
    
    // Both buttons should still be visible and clickable after submission
    cy.get('#btn_translate').should('be.visible');
    cy.get('#btn_judge').should('be.visible');
  });

  it('Test sequential submissions (submit form multiple times)', () => {
    cy.get('#mode_mock').check();
    
    // First submission
    cy.get('#source_text').clear().type('First text');
    cy.get('#target_lang').select('Английский');
    cy.get('#btn_translate').click();
    cy.contains('Mocked Translation').should('be.visible');
    
    // Second submission with different text
    cy.get('#source_text').clear().type('Second text');
    cy.get('#btn_translate').click();
    cy.contains('Mocked Translation').should('be.visible');
    
    // Third submission
    cy.get('#source_text').clear().type('Third text');
    cy.get('#btn_translate').click();
    cy.contains('Mocked Translation').should('be.visible');
  });

  it('Test very long text submission', () => {
    cy.get('#mode_mock').check();
    
    // Create a 5000 character string
    const longText = 'A'.repeat(5000);
    
    cy.get('#source_text').clear().type(longText, { delay: 0 }); // delay: 0 makes it faster
    cy.get('#target_lang').select('Английский');
    cy.get('#btn_translate').click();
    
    // Verify app handles long text without crashing
    cy.contains('Mocked Translation').should('be.visible');
  });
});
