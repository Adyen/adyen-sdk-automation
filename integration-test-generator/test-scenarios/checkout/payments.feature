# Source: CheckoutService-v72.json
# Endpoints: /payments, /sessions, /sessions/{sessionId}, /cardDetails, /paymentMethods

@integration @checkout @payments
Feature: Checkout payments
  Payment scenarios shared by all generated SDK integration test suites.

  Background:
    Given the Checkout API is configured for the TEST environment
    And the shared merchant account is available as "merchantAccount"

  @external @test-only @side-effect @response-200 @example-card-securedfields
  Scenario: Make a successful card payment
    Given a unique value is available as "reference"
    And the payment request is:
      """json
      {
        "amount": {
          "currency": "USD",
          "value": 1000
        },
        "reference": "${reference}",
        "paymentMethod": {
          "type": "scheme",
          "encryptedCardNumber": "test_4111111111111111",
          "encryptedExpiryMonth": "test_03",
          "encryptedExpiryYear": "test_2030",
          "encryptedSecurityCode": "test_737"
        },
        "returnUrl": "https://example.com/checkout/return",
        "merchantAccount": "${merchantAccount}"
      }
      """
    When the "payments" operation is called
    Then the operation succeeds
    And the response field "pspReference" is not empty
    And the response field "resultCode" equals "Authorised"

  @external @test-only @side-effect @response-201 @example-00-success
  Scenario: Create a payment session
    Given a unique value is available as "reference"
    And a unique idempotency key is available as "idempotencyKey"
    And the payment session request is:
      """json
      {
        "merchantAccount": "${merchantAccount}",
        "amount": {
          "value": 100,
          "currency": "EUR"
        },
        "returnUrl": "https://example.com/checkout/return",
        "reference": "${reference}",
        "countryCode": "NL"
      }
      """
    When the "sessions" operation is called
    Then the operation succeeds
    And the response field "id" is not empty

  @external @test-only @read-only @response-200 @example-basic
  Scenario: List brands for a card
    Given a unique idempotency key is available as "idempotencyKey"
    And the card details request is:
      """json
      {
        "merchantAccount": "${merchantAccount}",
        "cardNumber": "411111"
      }
      """
    When the "cardDetails" operation is called
    Then the operation succeeds
    And the response field "brands" is not empty
    And the response field "/brands/0/type" equals "visa"

  @external @test-only @read-only @response-200 @example-supported-brands
  Scenario: List supported brands for a card
    Given a unique idempotency key is available as "idempotencyKey"
    And the card details request is:
      """json
      {
        "merchantAccount": "${merchantAccount}",
        "cardNumber": "411111",
        "supportedBrands": [
          "visa",
          "mc",
          "amex"
        ]
      }
      """
    When the "cardDetails" operation is called
    Then the operation succeeds
    And the response field "/brands/0/type" equals "visa"
    And the response field "/brands/0/supported" equals true

  @external @test-only @read-only @response-200 @example-basic
  Scenario: List available payment methods
    Given a unique idempotency key is available as "idempotencyKey"
    And the payment methods request is:
      """json
      {
        "merchantAccount": "${merchantAccount}"
      }
      """
    When the "paymentMethods" operation is called
    Then the operation succeeds
    And the response field "paymentMethods" is not empty

