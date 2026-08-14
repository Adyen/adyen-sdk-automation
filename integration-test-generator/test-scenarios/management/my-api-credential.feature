# Source: ManagementService-v3.json
# Endpoint: /me

@integration @management @my-api-credential
Feature: Management API credential
  API credential scenarios shared by all generated SDK integration test suites.

  Background:
    Given the Management API is configured for the TEST environment

  @external @test-only @read-only @response-200
  Scenario: Get API credential details
    When the "getApiCredentialDetails" operation is called
    Then the operation succeeds with HTTP status 200
    And the response field "id" is not empty
    And the response field "active" equals true

  # Manual source: user-provided API credential payload, mapped by
  # adyen-main/configurationapi/src/main/java/com/adyen/configurationapi/iam/converter/user/UserConverter.java#toUserforMeEndpoint
  @contract-only @response-200 @example-manual-get-me-task
  Scenario: Validate the manually sourced 200 response
    Given documented response status 200
    And a TEST API credential ID is available as "apiCredentialId"
    And a TEST API credential username is available as "apiCredentialUsername"
    And a TEST API credential client key is available as "clientKey"
    And a TEST company name is available as "companyName"
    And a TEST allowed-origin ID is available as "allowedOriginId"
    And the manual response example "get-me-task" is:
      """json
      {
        "id": "${apiCredentialId}",
        "username": "${apiCredentialUsername}",
        "clientKey": "${clientKey}",
        "allowedIpAddresses": [
          "a",
          "b",
          "c"
        ],
        "roles": [
          "a",
          "b",
          "c"
        ],
        "active": true,
        "allowedOrigins": [
          {
            "id": "${allowedOriginId}",
            "domain": "https://www.adyen.com"
          }
        ],
        "companyName": "${companyName}"
      }
      """
    Then the manual response example matches the documented response schema
