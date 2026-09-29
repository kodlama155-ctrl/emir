package com.emir

import com.lagradost.cloudstream3.*
import com.lagradost.cloudstream3.utils.*
import org.jsoup.nodes.Element

class DiziKoreaProvider : MainAPI() {
    override var mainUrl = "https://dizikorea3.com"
    override var name = "DiziKorea"
    override val hasMainPage = true
    override var lang = "tr"
    override val hasDownloadSupport = true
    override val supportedTypes = setOf(TvType.TvSeries, TvType.Movie)

    override val mainPage = mainPageOf(
        "$mainUrl/kore-dizileri-izle-dq" to "Kore Dizileri",
        "$mainUrl/cin-dizileri" to "Çin Dizileri",
        "$mainUrl/japon-dizileri" to "Japon Dizileri",
        "$mainUrl/filmler" to "Filmler",
        "$mainUrl/tayland-dizileri" to "Tayland Dizileri",
        "$mainUrl/efsane-diziler" to "Efsane Diziler"
    )

    override suspend fun getMainPage(page: Int, request: MainPageRequest): HomePageResponse {
        val url = if (page == 1) request.data else "${request.data}/sayfa/$page"
        val doc = app.get(url).document
        val home = doc.select("a.poster-card, a.home-legend-card").mapNotNull { toSearchResponse(it) }
        return newHomePageResponse(request.name, home, hasNext = home.isNotEmpty())
    }

    private fun toSearchResponse(element: Element): SearchResponse? {
        val href = fixUrlNull(element.attr("href")) ?: return null
        val title = element.selectFirst(".poster-card-title, .title, img")?.let {
            if (it.hasClass("poster-card-title") || it.hasClass("title")) it.text().trim() else it.attr("alt").trim()
        } ?: element.attr("title").trim()

        val posterUrl = fixUrlNull(
            element.selectFirst("img")?.let {
                it.attr("src").ifBlank { it.attr("data-src") }
            }
        )
        val isMovie = href.contains("/film/")
        val type = if (isMovie) TvType.Movie else TvType.TvSeries

        return if (isMovie) {
            newMovieSearchResponse(title, href, type) {
                this.posterUrl = posterUrl
            }
        } else {
            newTvSeriesSearchResponse(title, href, type) {
                this.posterUrl = posterUrl
            }
        }
    }

    override suspend fun search(query: String): List<SearchResponse> {
        val url = "$mainUrl/?s=$query"
        val doc = app.get(url).document
        return doc.select("a.poster-card").mapNotNull { toSearchResponse(it) }
    }

    override suspend fun load(url: String): LoadResponse {
        val doc = app.get(url).document
        val title = doc.selectFirst("h1.series-title, h1.content-title, h1")?.text()?.trim() ?: "İçerik"
        val poster = fixUrlNull(
            doc.selectFirst(".series-hero-poster img, .series-hero-card img, div.poster img, img.poster")?.let {
                it.attr("src").ifBlank { it.attr("data-src") }
            }
        )
        val desc = doc.select(".series-about-text, .series-about-p, div.content-desc, div.story")
            .joinToString("\n\n") { it.text().trim() }
            .ifBlank { doc.selectFirst(".series-about-body, .series-about")?.text()?.trim() }

        val year = doc.selectFirst(".series-meta .meta-badge:matches(\\d{4})")?.text()?.trim()?.toIntOrNull()

        val isMovie = url.contains("/film/")

        if (isMovie) {
            return newMovieLoadResponse(title, url, TvType.Movie, url) {
                this.posterUrl = poster
                this.plot = desc
                this.year = year
            }
        }

        val episodes = mutableListOf<Episode>()
        doc.select("a.episode-item, .episode-list a").forEachIndexed { idx, el ->
            val epHref = fixUrlNull(el.attr("href")) ?: return@forEachIndexed
            val epNumStr = el.selectFirst(".ep-number")?.text()?.trim()
            val epNum = epNumStr?.toIntOrNull() ?: (idx + 1)
            val epName = el.selectFirst(".ep-title")?.text()?.trim() ?: "${epNum}. Bölüm"

            episodes.add(
                newEpisode(epHref) {
                    this.name = epName
                    this.episode = epNum
                }
            )
        }

        return newTvSeriesLoadResponse(title, url, TvType.TvSeries, episodes) {
            this.posterUrl = poster
            this.plot = desc
            this.year = year
        }
    }

    override suspend fun loadLinks(
        data: String,
        isCasting: Boolean,
        subtitleCallback: (SubtitleFile) -> Unit,
        callback: (ExtractorLink) -> Unit
    ): Boolean {
        val doc = app.get(data).document
        
        val iframes = mutableSetOf<String>()
        doc.select("iframe").forEach { iframe ->
            val src = iframe.attr("src").ifBlank { iframe.attr("data-src") }
            if (src.isNotBlank()) iframes.add(fixUrl(src))
        }

        for (ifr in iframes) {
            if (ifr.contains("playerdkorea") || ifr.contains("playerkorea") || ifr.contains("firevideoplayer")) {
                extractFirePlayer(ifr, data, subtitleCallback, callback)
            } else {
                loadExtractor(ifr, data, subtitleCallback, callback)
            }
        }
        return true
    }

    private suspend fun extractFirePlayer(
        url: String,
        referer: String,
        subtitleCallback: (SubtitleFile) -> Unit,
        callback: (ExtractorLink) -> Unit
    ) {
        try {
            val response = app.get(url, referer = referer).text
            
            val m3u8Regex = Regex("""(?:file|url)\s*:\s*["'](https?://[^"']+\.m3u8[^"']*)["']""")
            val mp4Regex = Regex("""(?:file|url)\s*:\s*["'](https?://[^"']+\.mp4[^"']*)["']""")

            m3u8Regex.find(response)?.groupValues?.get(1)?.let { m3u8Url ->
                M3u8Helper.generateM3u8(
                    name,
                    m3u8Url,
                    url
                ).forEach(callback)
            }

            mp4Regex.find(response)?.groupValues?.get(1)?.let { mp4Url ->
                callback(
                    newExtractorLink(
                        name = name,
                        source = name,
                        url = mp4Url,
                        type = ExtractorLinkType.VIDEO
                    )
                )
            }
        } catch (_: Exception) {}
    }
}
