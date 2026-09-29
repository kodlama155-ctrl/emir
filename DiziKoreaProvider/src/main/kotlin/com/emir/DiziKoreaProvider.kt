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

    data class SearchItem(
        val title: String,
        val url: String,
        val poster: String? = null,
        val type: String? = null
    )

    data class SearchApiResponse(
        val success: Boolean = false,
        val items: List<SearchItem>? = null
    )

    override suspend fun search(query: String): List<SearchResponse> {
        return try {
            val apiUrl = "$mainUrl/ara?q=${query.trim().replace(" ", "+")}"
            val res = app.get(
                apiUrl,
                headers = mapOf(
                    "X-Requested-With" to "XMLHttpRequest",
                    "Referer" to "$mainUrl/"
                )
            ).parsedSafe<SearchApiResponse>()

            res?.items?.mapNotNull { item ->
                val href = fixUrlNull(item.url) ?: return@mapNotNull null
                val isMovie = item.type == "movie" || href.contains("/film/")
                val type = if (isMovie) TvType.Movie else TvType.TvSeries
                val posterUrl = fixUrlNull(item.poster)

                if (isMovie) {
                    newMovieSearchResponse(item.title, href, type) {
                        this.posterUrl = posterUrl
                    }
                } else {
                    newTvSeriesSearchResponse(item.title, href, type) {
                        this.posterUrl = posterUrl
                    }
                }
            } ?: emptyList()
        } catch (_: Exception) {
            emptyList()
        }
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
        val seasonContainers = doc.select("div.episode-list[data-season]")
        if (seasonContainers.isNotEmpty()) {
            for (container in seasonContainers) {
                val seasonNum = container.attr("data-season").toIntOrNull() ?: 1
                container.select("a.episode-item").forEachIndexed { idx, el ->
                    val epHref = fixUrlNull(el.attr("href")) ?: return@forEachIndexed
                    val epNum = el.selectFirst(".ep-number")?.text()?.trim()?.toIntOrNull() ?: (idx + 1)
                    val epName = el.selectFirst(".ep-title")?.text()?.trim() ?: "${epNum}. Bölüm"

                    episodes.add(
                        newEpisode(epHref) {
                            this.name = epName
                            this.season = seasonNum
                            this.episode = epNum
                        }
                    )
                }
            }
        } else {
            doc.select("a.episode-item, .episode-list a").forEachIndexed { idx, el ->
                val epHref = fixUrlNull(el.attr("href")) ?: return@forEachIndexed
                val epNum = el.selectFirst(".ep-number")?.text()?.trim()?.toIntOrNull() ?: (idx + 1)
                val epName = el.selectFirst(".ep-title")?.text()?.trim() ?: "${epNum}. Bölüm"

                episodes.add(
                    newEpisode(epHref) {
                        this.name = epName
                        this.season = 1
                        this.episode = epNum
                    }
                )
            }
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
            val src = iframe.attr("data-src").ifBlank { iframe.attr("src") }
            if (src.isNotBlank()) {
                val fixed = fixUrl(src)
                iframes.add(fixed)
                if (fixed.contains("vidmoly.biz")) {
                    iframes.add(fixed.replace("vidmoly.biz", "vidmoly.to"))
                    iframes.add(fixed.replace("vidmoly.biz", "vidmoly.net"))
                }
            }
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

    data class VideoApiResponse(
        val videoSource: String? = null,
        val securedLink: String? = null
    )

    private suspend fun extractFirePlayer(
        url: String,
        referer: String,
        subtitleCallback: (SubtitleFile) -> Unit,
        callback: (ExtractorLink) -> Unit
    ) {
        try {
            val videoId = if (url.contains("/video/")) {
                url.substringAfter("/video/").substringBefore("?").substringBefore("/")
            } else if (url.contains("data=")) {
                url.substringAfter("data=").substringBefore("&").substringBefore("#")
            } else ""

            if (videoId.isNotBlank()) {
                val origin = if (url.contains("://")) {
                    val parts = url.split("/")
                    "${parts[0]}//${parts[2]}"
                } else "https://playerdkorea.xyz"

                val apiUrl = "$origin/player/index.php?data=$videoId&do=getVideo"
                val apiResponse = app.post(
                    apiUrl,
                    headers = mapOf(
                        "Referer" to url,
                        "Origin" to origin,
                        "X-Requested-With" to "XMLHttpRequest",
                        "Content-Type" to "application/x-www-form-urlencoded; charset=UTF-8"
                    ),
                    data = mapOf(
                        "hash" to videoId,
                        "r" to referer
                    )
                ).parsedSafe<VideoApiResponse>()

                val m3u8Url = apiResponse?.securedLink ?: apiResponse?.videoSource
                if (!m3u8Url.isNullOrBlank()) {
                    M3u8Helper.generateM3u8(
                        source = name,
                        name = name,
                        streamUrl = m3u8Url,
                        referer = "$origin/"
                    ).forEach(callback)
                    return
                }
            }
        } catch (_: Exception) {}

        try {
            loadExtractor(url, referer, subtitleCallback, callback)
        } catch (_: Exception) {}
    }
}
