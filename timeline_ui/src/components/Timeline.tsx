import React, { useMemo } from 'react'
import { format } from 'date-fns'
import NewsCard from './NewsCard'
import { NewsItem, useNewsStore, getFilteredNews } from '../store/newsStore'

interface TimelineProps {
  filter: 'featured' | 'all' | 'bookmarks'
  width?: number
}

const Timeline: React.FC<TimelineProps> = ({ filter, width = 800 }) => {
  const { news, selectedTag, searchQuery, toggleBookmark } = useNewsStore()

  const groupedNews = useMemo(() => {
    const filtered = getFilteredNews(news, filter, selectedTag, searchQuery)
    const groups = new Map<string, { timeKey: string; timeDisplay: string; news: NewsItem[] }>()
    
    filtered.forEach(item => {
      const date = new Date(item.first_crawl_time)
      const timeKey = format(date, 'HH:mm')
      if (!groups.has(timeKey)) {
        groups.set(timeKey, { timeKey, timeDisplay: timeKey, news: [] })
      }
      groups.get(timeKey)!.news.push(item)
    })
    
    return Array.from(groups.values()).sort((a, b) => b.timeKey.localeCompare(a.timeKey))
  }, [news, filter, selectedTag, searchQuery])

  if (groupedNews.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <div className="text-lg text-text-secondary mb-2">暂无数据</div>
        <div className="text-sm text-text-muted">切换筛选条件查看内容</div>
      </div>
    )
  }

  return (
    <div className="flex justify-center">
      <div style={{ width: `${width}px` }} className="relative">
        <div className="absolute left-20 top-5 bottom-4 w-px bg-gradient-to-b from-accent-primary/50 via-accent-primary/30 to-transparent" />
        
        {groupedNews.map((group) => (
          <div key={group.timeKey} className="flex mb-8 last:mb-0">
            <div className="w-20 flex-shrink-0 text-right pr-4 pt-3">
              <span className="text-lg font-bold text-accent-primary">{group.timeDisplay}</span>
            </div>
            <div className="relative w-4 flex-shrink-0">
              <div className="absolute left-0 top-5 -translate-x-1/2 z-10">
                <div className="w-3 h-3 rounded-full bg-accent-primary shadow-neon" />
              </div>
            </div>
            <div className="flex-1 space-y-2">
              {group.news.map(item => (
                <NewsCard key={item.id} news={item} onBookmark={toggleBookmark} />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default Timeline
