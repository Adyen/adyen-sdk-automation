@integration @checkout @payments
Feature: Checkout payments
  Payment scenarios shared by all generated SDK integration test suites.

  Background:
    Given the Checkout API is configured for the TEST environment
    And the shared merchant account is available as "merchantAccount"

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
        "returnUrl": "https://your-company.example.com/...",
        "merchantAccount": "${merchantAccount}"
      }
      """
    When the "payments" operation is called
    Then the operation succeeds
    And the response field "pspReference" is not empty
    And the response field "resultCode" equals "Authorised"

  Scenario: Reject a payment with an invalid currency
    Given a unique value is available as "reference"
    And the payment request is:
      """json
      {
        "amount": {
          "currency": "INVALID",
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
        "returnUrl": "https://your-company.example.com/...",
        "merchantAccount": "${merchantAccount}"
      }
      """
    When the "payments" operation is called
    Then the operation fails with HTTP status 422
    And the API error field "errorCode" equals "138"
    And the API error field "errorType" equals "validation"
    And the API error message contains "currency", ignoring case
