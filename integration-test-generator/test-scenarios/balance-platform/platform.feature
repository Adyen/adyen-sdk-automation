# Source: BalancePlatformService-v2.json
# Endpoint: /balancePlatforms/{id}

@integration @balance-platform @platform
Feature: Balance Platform platform
  Platform scenarios shared by all generated SDK integration test suites.

  Background:
    Given the Balance Platform API is configured for the TEST environment

  @external @test-only @manual @read-only @response-200 @example-success
  Scenario: Retrieve a balance platform
    Given path parameter "id" comes from environment "API_LIBRARIES_ADYEN_BALANCE_PLATFORM_ID"
    When the "getBalancePlatform" operation is called
    Then the operation succeeds
    And the response field "id" equals "${id}"
