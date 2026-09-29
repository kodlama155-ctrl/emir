package com.emir

import com.lagradost.cloudstream3.plugins.CloudstreamPlugin
import com.lagradost.cloudstream3.plugins.Plugin
import android.content.Context

@CloudstreamPlugin
class DiziKoreaPlugin: Plugin() {
    override fun load(context: Context) {
        registerMainAPI(DiziKoreaProvider())
    }
}
