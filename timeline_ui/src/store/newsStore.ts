import { create } from 'zustand'

export interface NewsItem {
  id: number
  title: string
  title_zh?: string
  description?: string
  platform_id: string
  platform_name: string
  platform_category: string
  platform_color?: string
  rank: number
  url: string
  first_crawl_time: string
  last_crawl_time: string
  crawl_count: number
  hot_value?: string
  icon_url?: string
  source_updated_ts?: number
  // AI
  ai_tags?: string[]
  tags?: string[]  // alias used in UI
  ai_heat_score: number
  ai_reason?: string
  // Events
  event_id: number | null
  related_count: number
  // Personal
  relevance_score?: number
  matched_interests?: { tag: string; relevance: number; priority: number }[]
  personal_score: number
  is_breakthrough?: boolean
  primary_interest?: string
  is_bookmarked: boolean
}

export interface Platform {
  id: string
  name: string
  category: string
  color: string
  news_count: number
  latest_updated_ts: number
  latest_crawl_time: string
}

export interface Interest {
  id: number
  tag: string
  description: string
  priority: number
  hits: number
  avg_score: number
}

export interface TimelineEvent {
  event_id: number
  event_name: string
  summary: string
  news_count: number
  platforms: string[]
  platform_ids: string[]
  heat: number
  rising: boolean
  rep_title: string
  rep_url: string
  tags?: string[]
}

export interface Statistics {
  total: number
  analyzed: number
  tags_count: number
  heat_ge_80: number
  events: number
  interest_hits: number
  breakthrough: number
  last_updated: string
}

interface NewsState {
  news: NewsItem[]
  platforms: Platform[]
  interests: Interest[]
  events: TimelineEvent[]
  statistics: Statistics | null
  loading: boolean
  error: string | null

  fetchAll: () => Promise<void>
  toggleBookmark: (id: number) => void
  bookmarks: Set<number>
}

const API_BASE_URL = (import.meta as any).env?.DEV
  ? 'http://localhost:8001/api/timeline'
  : '/api/timeline'

export const useNewsStore = create<NewsState>((set, get) => ({
  news: [],
  platforms: [],
  interests: [],
  events: [],
  statistics: null,
  loading: false,
  error: null,
  bookmarks: new Set<number>(),

  fetchAll: async () => {
    set({ loading: true, error: null })
    try {
      const [feedR, newsR, rssR, platR, intR, evtR, statR] = await Promise.all([
        fetch(`${API_BASE_URL}/feed?limit=500`).then(r => r.json()).catch(() => ({ success: false, data: [] })),
        fetch(`${API_BASE_URL}/news?filter=all&limit=1000`).then(r => r.json()).catch(() => ({ success: false, data: [] })),
        fetch(`${API_BASE_URL}/rss?limit=300`).then(r => r.json()).catch(() => ({ success: false, data: [] })),
        fetch(`${API_BASE_URL}/platforms`).then(r => r.json()).catch(() => ({ success: false, data: [] })),
        fetch(`${API_BASE_URL}/interests`).then(r => r.json()).catch(() => ({ success: false, data: [] })),
        fetch(`${API_BASE_URL}/events`).then(r => r.json()).catch(() => ({ success: false, data: [] })),
        fetch(`${API_BASE_URL}/stats`).then(r => r.json()).catch(() => ({ success: false, data: null })),
      ])

      const feedById = new Map<number, any>()
      ;(feedR.data || []).forEach((x: any) => feedById.set(x.id, x))

      // Merge news + rss into a unified list; overlay feed fields when available
      const rawNews: any[] = [...(newsR.data || []), ...(rssR.data || [])]
      const merged: NewsItem[] = rawNews.map(n => {
        const f = feedById.get(n.id)
        const tags: string[] = Array.isArray(n.ai_tags) ? n.ai_tags : []
        const rel = f?.relevance_score ?? (n.event_id ? 0.7 : 0.4)
        const heat = (n.ai_heat_score || 0) / 100
        const related = n.related_count || 0
        const pw = 1.0
        const score = f?.personal_score ??
          Math.round((0.6 * rel + 0.15 * heat + 0.15 * Math.min(related / 10, 1) + 0.1 * pw) * 100)
        return {
          ...n,
          tags,
          relevance_score: f?.relevance_score ?? rel,
          matched_interests: f?.matched_interests || [],
          personal_score: score,
          is_breakthrough: f?.is_breakthrough || false,
          primary_interest: f?.primary_interest || '',
        } as NewsItem
      })

      // Fallback stats if endpoint old-shape
      const s = statR.data || {}
      const stats: Statistics = {
        total: s.total_news || merged.length,
        analyzed: s.analyzed_news || 0,
        tags_count: s.total_tags || 0,
        heat_ge_80: merged.filter(n => (n.ai_heat_score || 0) >= 80).length,
        events: (evtR.data || []).length,
        interest_hits: merged.filter(n => (n.relevance_score || 0) >= 0.3).length,
        breakthrough: merged.filter(n => n.is_breakthrough).length,
        last_updated: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
      }

      set({
        news: merged,
        platforms: platR.data || [],
        interests: intR.data || [],
        events: evtR.data || [],
        statistics: stats,
        loading: false,
      })
    } catch (e) {
      console.error(e)
      set({ loading: false, error: e instanceof Error ? e.message : 'unknown' })
    }
  },

  toggleBookmark: (id: number) => {
    set(state => {
      const n = new Set(state.bookmarks)
      n.has(id) ? n.delete(id) : n.add(id)
      return { bookmarks: n }
    })
  },
}))
