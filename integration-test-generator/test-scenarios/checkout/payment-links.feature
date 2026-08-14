# Source: CheckoutService-v72.json
# Endpoint: /paymentLinks

@integration @checkout @payment-links
Feature: Checkout payment links
  Payment link scenarios shared by all generated SDK integration test suites.

  Background:
    Given the Checkout API is configured for the TEST environment
    And the shared merchant account is available as "merchantAccount"

  @external @test-only @side-effect @response-201 @example-basic
  Scenario: Create a payment link
    Given a unique value is available as "reference"
    And a unique value is available as "shopperReference"
    And a unique idempotency key is available as "idempotencyKey"
    And the payment link request is:
      """json
      {
        "reference": "${reference}",
        "amount": {
          "value": 1250,
          "currency": "BRL"
        },
        "countryCode": "BR",
        "merchantAccount": "${merchantAccount}",
        "shopperReference": "${shopperReference}",
        "shopperEmail": "test@email.com",
        "shopperLocale": "pt-BR",
        "billingAddress": {
          "street": "Roque Petroni Jr",
          "postalCode": "59000060",
          "city": "São Paulo",
          "houseNumberOrName": "999",
          "country": "BR",
          "stateOrProvince": "SP"
        },
        "deliveryAddress": {
          "street": "Roque Petroni Jr",
          "postalCode": "59000060",
          "city": "São Paulo",
          "houseNumberOrName": "999",
          "country": "BR",
          "stateOrProvince": "SP"
        }
      }
      """
    When the "paymentLinks" operation is called
    Then the operation succeeds with HTTP status 201
    And the response field "id" is not empty
