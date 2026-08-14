# Source: CheckoutService-v72.json
# Endpoints: /payments, /sessions/{sessionId}, /cardDetails

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
    Then the operation succeeds with HTTP status 200
    And the response field "pspReference" is not empty
    And the response field "resultCode" equals "Authorised"

  @contract-only @response-400 @example-generic
  Scenario: Validate the documented 400 response
    Given documented response status 400
    And response example "generic"
    Then the response example matches the documented response schema

  @contract-only @response-401 @example-generic
  Scenario: Validate the documented 401 response
    Given documented response status 401
    And response example "generic"
    Then the response example matches the documented response schema

  @contract-only @response-403 @example-generic
  Scenario: Validate the documented 403 response
    Given documented response status 403
    And response example "generic"
    Then the response example matches the documented response schema

  @external @test-only @side-effect @response-422
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
        "returnUrl": "https://example.com/checkout/return",
        "merchantAccount": "${merchantAccount}"
      }
      """
    When the "payments" operation is called
    Then the operation fails with HTTP status 422
    And the API error field "errorCode" equals "138"
    And the API error field "errorType" equals "validation"
    And the API error message contains "currency", ignoring case

  @contract-only @response-500 @example-generic
  Scenario: Validate the documented 500 response
    Given documented response status 500
    And response example "generic"
    Then the response example matches the documented response schema

  @contract-only @response-200 @example-success
  Scenario: Validate the documented payment session result
    Given documented response status 200
    And the API Explorer response example "success" is:
      """json
      {
        "id": "CS12345678",
        "status": "completed"
      }
      """
    Then the response example matches the documented response schema

  @external @test-only @side-effect @response-200 @example-klarna
  Scenario: Start a Klarna payment
    Given a unique value is available as "reference"
    And a unique value is available as "shopperReference"
    And a unique idempotency key is available as "idempotencyKey"
    And the payment request is:
      """json
      {
        "merchantAccount": "${merchantAccount}",
        "reference": "${reference}",
        "paymentMethod": {
          "type": "klarna"
        },
        "amount": {
          "currency": "SEK",
          "value": 1000
        },
        "shopperLocale": "en_US",
        "countryCode": "SE",
        "telephoneNumber": "+46 840 839 298",
        "shopperEmail": "youremail@email.com",
        "shopperName": {
          "firstName": "Testperson-se",
          "lastName": "Approved"
        },
        "shopperReference": "${shopperReference}",
        "billingAddress": {
          "city": "Ankeborg",
          "country": "SE",
          "houseNumberOrName": "1",
          "postalCode": "12345",
          "street": "Stargatan"
        },
        "deliveryAddress": {
          "city": "Ankeborg",
          "country": "SE",
          "houseNumberOrName": "1",
          "postalCode": "12345",
          "street": "Stargatan"
        },
        "returnUrl": "https://example.com/checkout/return",
        "lineItems": [
          {
            "quantity": 1,
            "amountExcludingTax": 331,
            "taxPercentage": 2100,
            "description": "Shoes",
            "id": "Item #1",
            "taxAmount": 69,
            "amountIncludingTax": 400,
            "productUrl": "https://example.com/products/shoes",
            "imageUrl": "https://example.com/images/shoes.jpg"
          },
          {
            "quantity": 2,
            "amountExcludingTax": 248,
            "taxPercentage": 2100,
            "description": "Socks",
            "id": "Item #2",
            "taxAmount": 52,
            "amountIncludingTax": 300,
            "productUrl": "https://example.com/products/socks",
            "imageUrl": "https://example.com/images/socks.jpg"
          }
        ]
      }
      """
    When the "payments" operation is called
    Then the operation succeeds with HTTP status 200
    And the response field "action" is not empty

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
    Then the operation succeeds with HTTP status 200
    And the response field "/brands/0/type" equals "visa"
    And the response field "/brands/0/supported" equals true
