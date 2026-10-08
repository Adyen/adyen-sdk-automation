# Source: LegalEntityService-v4.json
# Endpoint: /legalEntities

@integration @legal-entity-management @legal-entities
Feature: Legal Entity Management legal entities
  Legal entity scenarios shared by all generated SDK integration test suites.

  Background:
    Given the Legal Entity Management API is configured for the TEST environment

  @external @test-only @side-effect @response-200 @example-create-legal-entity-individual-nl
  Scenario: Create a legal entity for an individual residing in the Netherlands
    Given the legal entity request is:
      """json
      {
        "type": "individual",
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
          "phone": {
            "number": "+31858888138",
            "type": "mobile"
          },
          "birthData": {
            "dateOfBirth": "1990-06-21"
          },
          "email": "s.eller@example.com"
        }
      }
      """
    When the "createLegalEntity" operation is called
    Then the operation succeeds
    And the response field "id" is not empty
    And the response field "type" equals "individual"
