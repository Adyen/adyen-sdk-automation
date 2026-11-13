package com.adyen.sdk

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

class GoServiceLayoutTest {

    @Test
    fun `multi-tag service uses its id as package and name as service name`() {
        val layout = GoServiceLayout.of(Service(name = "Checkout", version = 71))

        assertThat(layout.packageName).isEqualTo("checkout")
        assertThat(layout.directory).isEqualTo("checkout")
        assertThat(layout.serviceName).isEqualTo("Checkout")
        assertThat(layout.supportingFile).isEqualTo("client.go")
        assertThat(layout.deploysClient(listOf("api_payments.go", "api_donations.go", "client.go"))).isTrue()
    }

    @Test
    fun `multi-tag service deploys its client even with a single tag`() {
        val layout = GoServiceLayout.of(Service(name = "ForeignExchange", version = 1))

        assertThat(layout.deploysClient(listOf("api_rates.go", "client.go"))).isTrue()
    }

    @Test
    fun `small service with a single tag has no client`() {
        val layout = GoServiceLayout.of(Service(name = "BinLookup", version = 54, small = true))

        assertThat(layout.packageName).isEqualTo("binlookup")
        assertThat(layout.serviceName).isEqualTo("BinLookup")
        assertThat(layout.deploysClient(listOf("api_general.go", "client.go", "model_amount.go"))).isFalse()
    }

    @Test
    fun `small service with several tags keeps its client`() {
        val layout = GoServiceLayout.of(Service(name = "Payment", version = 68, small = true))

        assertThat(layout.deploysClient(listOf("api_modifications.go", "api_payments.go", "client.go"))).isTrue()
    }

    @Test
    fun `webhook package is singular, renders the handler and has no client`() {
        val layout = GoServiceLayout.of(Service(name = "AcsWebhooks", version = 1))

        assertThat(layout.packageName).isEqualTo("acswebhook")
        assertThat(layout.directory).isEqualTo("acswebhook")
        assertThat(layout.supportingFile).isEqualTo("webhook_handler.go")
        assertThat(layout.deploysClient(listOf("api_general.go", "api_other.go", "client.go"))).isFalse()
    }

    @Test
    fun `legacy names keep their public import paths and endpoints`() {
        val payment = GoServiceLayout.of(Service(name = "Payment", version = 68, small = true))
        val payout = GoServiceLayout.of(Service(name = "Payout", version = 68))
        val legalEntity = GoServiceLayout.of(Service(name = "LegalEntityManagement", version = 3))

        assertThat(payment.packageName).isEqualTo("payments")
        assertThat(payment.serviceName).isEmpty()
        assertThat(payout.packageName).isEqualTo("payout")
        assertThat(payout.serviceName).isEmpty()
        assertThat(legalEntity.packageName).isEqualTo("legalentity")
        assertThat(legalEntity.serviceName).isEqualTo("LegalEntity")
    }
}
