# Source: CheckoutService-v72.json
# Endpoint: /storedPaymentMethods

@integration @checkout @recurring
Feature: Checkout recurring
  Recurring scenarios shared by all generated SDK integration test suites.

  Background:
    Given the Checkout API is configured for the TEST environment

  @contract-only @response-200 @example-success
  Scenario: Validate the documented 200 response
    Given documented response status 200
    And response example "success"
    Then the response example matches the documented response schema
