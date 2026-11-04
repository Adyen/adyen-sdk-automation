@integration @checkout @donations
Feature: Checkout donations
  Donation scenarios shared by all generated SDK integration test suites.

  Background:
    Given the Checkout API is configured for the TEST environment
    And the shared merchant account is available as "merchantAccount"

  Scenario: Get donation campaigns
    Given the donation campaigns request is:
      """json
      {
        "merchantAccount": "${merchantAccount}",
        "currency": "EUR"
      }
      """
    When the "donationCampaigns" operation is called
    Then the operation succeeds
    And the response field "donationCampaigns" is an array
