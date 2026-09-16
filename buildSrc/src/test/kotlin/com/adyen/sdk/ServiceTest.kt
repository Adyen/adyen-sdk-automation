package com.adyen.sdk

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

class ServiceTest {

    @Test
    fun `filename follows the spec naming convention`() {
        assertThat(Service(name = "Checkout", version = 71).filename).isEqualTo("CheckoutService-v71.json")
    }
}
