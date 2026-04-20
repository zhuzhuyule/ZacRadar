import { create } from 'zustand'

export interface NewsItem {
  id: number
  title: string
  platform_name: string
  rank: number
  url: string
  first_crawl_time: string
  last_crawl_time: string
  crawl_count: number
  ai_tags: string[]
  ai_heat_score: number
  ai_reason: string
  event_id: number | null
  related_count: number
  is_bookmarked: boolean
}

export interface Statistics {
  total_news: number
  analyzed_news: number
  total_tags: number
  total_events: number
  total_bookmarks: number
}

interface NewsState {
  // 数据
  news: NewsItem[]
  tags: string[]
  sources: string[]
  statistics: Statistics | null
  
  // 状态
  loading: boolean
  error: string | null
  
  // 筛选
  filter: 'featured' | 'all' | 'bookmarks'
  selectedTag: string | null
  searchQuery: string
  
  // Actions
  fetchNews: () => Promise<void>
  fetchTags: () => Promise<void>
  fetchStatistics: () => Promise<void>
  toggleBookmark: (newsId: number) => Promise<void>
  setFilter: (filter: 'featured' | 'all' | 'bookmarks') => void
  setSelectedTag: (tag: string | null) => void
  setSearchQuery: (query: string) => void
}

// API 配置 - 开发和生产环境自适应
const API_BASE_URL = (import.meta as any).env?.DEV 
  ? 'http://localhost:8001/api/timeline'  // 开发模式直接连接 API 服务器
  : '/api/timeline'  // 生产模式使用相对路径（由 MCP 服务器代理）

export const useNewsStore = create<NewsState>((set, get) => ({
  // 初始状态
  news: [],
  tags: [],
  sources: [],
  statistics: null,
  loading: false,
  error: null,
  filter: 'featured',
  selectedTag: null,
  searchQuery: '',

  // 获取新闻数据
  fetchNews: async () => {
    set({ loading: true, error: null })
    try {
      const { filter, selectedTag, searchQuery } = get()
      
      // 构建查询参数
      const params = new URLSearchParams()
      params.set('filter', filter)
      if (selectedTag) params.set('tag', selectedTag)
      if (searchQuery) params.set('search', searchQuery)
      
      const response = await fetch(`${API_BASE_URL}/news?${params}`)
      const result = await response.json()
      
      if (!result.success) {
        throw new Error(result.error || 'API 请求失败')
      }
      
      set({
        news: result.data,
        sources: Array.from(new Set(result.data.map((n: NewsItem) => n.platform_name))),
        loading: false,
      })
      
      // 获取统计数据
      get().fetchStatistics()
    } catch (error) {
      console.error('获取新闻失败:', error)
      set({
        news: [],
        loading: false,
        error: error instanceof Error ? error.message : '未知错误',
      })
    }
  },

  // 获取标签列表
  fetchTags: async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/tags`)
      const result = await response.json()
      if (result.success) {
        set({ tags: result.data })
      }
    } catch (error) {
      console.error('获取标签失败:', error)
      // 从新闻数据中提取
      const allTags = new Set<string>()
      get().news.forEach(n => n.ai_tags.forEach(tag => allTags.add(tag)))
      set({ tags: Array.from(allTags) })
    }
  },

  // 获取统计数据
  fetchStatistics: async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/stats`)
      const result = await response.json()
      if (result.success) {
        set({ statistics: result.data })
      }
    } catch (error) {
      console.error('获取统计数据失败:', error)
    }
  },

  // 切换收藏状态
  toggleBookmark: async (newsId: number) => {
    try {
      const response = await fetch(`${API_BASE_URL}/bookmark/${newsId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: 'default' }),
      })
      const result = await response.json()
      
      if (!result.success) {
        throw new Error(result.error || '操作失败')
      }
      
      set(state => ({
        news: state.news.map(n =>
          n.id === newsId ? { ...n, is_bookmarked: result.data.is_bookmarked } : n
        ),
      }))
    } catch (error) {
      console.error('切换收藏失败:', error)
    }
  },

  // 设置筛选
  setFilter: (filter) => set({ filter }),

  // 设置选中标签
  setSelectedTag: (tag) => set({ selectedTag: tag }),

  // 设置搜索关键词
  setSearchQuery: (query) => set({ searchQuery: query }),
}))

// 辅助函数：获取筛选后的新闻
export const getFilteredNews = (
  news: NewsItem[],
  filter: string,
  selectedTag: string | null,
  searchQuery: string
): NewsItem[] => {
  let filtered = news

  // 按筛选条件过滤
  if (filter === 'featured') {
    filtered = filtered.filter(n => n.ai_heat_score >= 80)
  } else if (filter === 'bookmarks') {
    filtered = filtered.filter(n => n.is_bookmarked)
  }

  // 按标签过滤
  if (selectedTag) {
    filtered = filtered.filter(n => n.ai_tags.includes(selectedTag))
  }

  // 按搜索关键词过滤
  if (searchQuery) {
    const query = searchQuery.toLowerCase()
    filtered = filtered.filter(n =>
      n.title.toLowerCase().includes(query) ||
      n.ai_reason?.toLowerCase().includes(query) ||
      n.ai_tags.some(tag => tag.toLowerCase().includes(query))
    )
  }

  return filtered
}
