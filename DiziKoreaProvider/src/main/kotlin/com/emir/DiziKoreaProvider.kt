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
        val title = element.selectFirst("img")?.attr("alt")?.trim() ?: element.attr("title").trim()
        val posterUrl = fixUrlNull(element.selectFirst("img")?.attr("src"))
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
        val title = doc.selectFirst("h1.content-title, h1")?.text()?.trim() ?: "İçerik"
        val poster = fixUrlNull(doc.selectFirst("div.poster img, img.poster")?.attr("src"))
        val desc = doc.selectFirst("div.content-desc, div.story")?.text()?.trim()
        val isMovie = url.contains("/film/")

        if (isMovie) {
            return newMovieLoadResponse(title, url, TvType.Movie, url) {
                this.posterUrl = poster
                this.plot = desc
            }
        }

        val episodes = mutableListOf<Episode>()
        doc.select("div.episodes-list a, a.episode-item, div.season-list a").forEachIndexed { idx, el ->
            val epHref = fixUrlNull(el.attr("href")) ?: return@forEachIndexed
            val epName = el.text().trim().ifBlank { "${idx + 1}. Bölüm" }
            episodes.add(
                newEpisode(epHref) {
                    this.name = epName
                    this.episode = idx + 1
                }
            )
        }

        if (episodes.isEmpty()) {
            episodes.add(newEpisode(url) { this.name = "1. Bölüm"; this.episode = 1 })
        }

        return newTvSeriesLoadResponse(title, url, TvType.TvSeries, episodes) {
            this.posterUrl = poster
            this.plot = desc
        }
    }

    override suspend fun loadLinks(
        data: String,
        isCasting: Boolean,
        subtitleCallback: (SubtitleFile) -> Unit,
        callback: (ExtractorLink) -> Unit
    ): Boolean {
        val doc = app.get(data).document
        val iframes = doc.select("iframe").mapNotNull { it.attr("src") }
        
        for (ifr in iframes) {
            val fullIfr = fixUrl(ifr)
            loadExtractor(fullIfr, data, subtitleCallback, callback)
        }
        return true
    }
}
