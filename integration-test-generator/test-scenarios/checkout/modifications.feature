@integration @checkout @modifications
Feature: Checkout modifications
  Payment modification scenarios shared by all generated SDK integration test suites.

  Background:
    Given the Checkout API is configured for the TEST environment
    And the shared merchant account is available as "merchantAccount"

  Scenario: Capture an authorised payment
    Given an authorised uncaptured payment of 2000 EUR is available as "paymentPspReference"
    And a unique value is available as "reference"
    And the payment capture request is:
      """json
      {
        "reference": "${reference}",
        "merchantAccount": "${merchantAccount}",
        "amount": {
          "value": 2000,
          "currency": "EUR"
        }
      }
      """
    When the "captureAuthorisedPayment" operation is called with "paymentPspReference"
    Then the operation succeeds
    And the response field "pspReference" is not empty
    And the response field "paymentPspReference" equals "${paymentPspReference}"
    And the response field "status" equals "received"
