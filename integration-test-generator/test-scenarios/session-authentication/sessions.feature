@integration @session-authentication @sessions
Feature: Session authentication
  Session authentication scenarios shared by all generated SDK integration test suites.

  Background:
    Given the Session Authentication API is configured for the TEST environment

  Scenario: Create a session token for onboarding components
    Given an onboarding-eligible legal entity is available as "legalEntityId"
    And the authentication session request is:
      """json
      {
        "allowOrigin": "https://www.your-website.com",
        "product": "onboarding",
        "policy": {
          "resources": [
            {
              "type": "legalEntity",
              "legalEntityId": "${legalEntityId}"
            }
          ],
          "roles": [
            "createTransferInstrumentComponent",
            "manageTransferInstrumentComponent"
          ]
        }
      }
      """
    When the "createAuthenticationSession" operation is called
    Then the operation succeeds
    And the response field "id" is not empty
    And the response field "token" is not empty
