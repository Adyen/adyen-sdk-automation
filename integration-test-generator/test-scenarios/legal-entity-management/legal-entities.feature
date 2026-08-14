@integration @legal-entity-management @legal-entities
Feature: Legal Entity Management legal entities
  Legal entity scenarios shared by all generated SDK integration test suites.

  Background:
    Given the Legal Entity Management API is configured for the TEST environment

  Scenario: Create a new individual legal entity
    Given a unique value is available as "reference"
    And a unique test email address is available as "email"
    And the legal entity request is:
      """json
      {
        "type": "individual",
        "reference": "${reference}",
        "individual": {
          "residentialAddress": {
            "city": "Amsterdam",
            "country": "NL",
            "postalCode": "1011DJ",
            "street": "Simon Carmiggeltstraat 6 - 50"
          },
          "name": {
            "firstName": "Shelly",
            "lastName": "Eller"
          },
          "birthData": {
            "dateOfBirth": "1990-06-21"
          },
          "email": "${email}"
        }
      }
      """
    When the "createLegalEntity" operation is called
    Then the operation succeeds
    And the response field "id" is not empty
    And the response field "type" equals "individual"
    And the response field "reference" equals "${reference}"
