# Source: CheckoutService-v72.json
# Endpoint: /orders

@integration @checkout @orders
Feature: Checkout orders
  Order scenarios shared by all generated SDK integration test suites.

  Background:
    Given the Checkout API is configured for the TEST environment
    And the shared merchant account is available as "merchantAccount"

  @external @test-only @side-effect @response-200 @example-basic
  Scenario: Create an order
    Given a unique value is available as "reference"
    And a unique idempotency key is available as "idempotencyKey"
    And the order request is:
      """json
      {
        "reference": "${reference}",
        "amount": {
          "value": 2500,
          "currency": "EUR"
        },
        "merchantAccount": "${merchantAccount}"
      }
      """
    When the "orders" operation is called
    Then the operation succeeds
    And the response field "resultCode" equals "Success"
