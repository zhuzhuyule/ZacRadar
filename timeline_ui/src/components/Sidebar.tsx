import React, { useState } from 'react'
import clsx from 'clsx'
import { useNewsStore } from '../store/newsStore'

interface SidebarProps {
  filter: 'featured' | 'all' | 'bookmarks'
  onFilterChange: (filter: 'featured' | 'all' | 'bookmarks') => void
}

const cardWidthOptions = [
  { value: 800, label: '800' },
  { value: 1000, label: '1000' },
  { value: 1200, label: '1200' },
]

const Sidebar: React.FC<SidebarProps> = ({ filter, onFilterChange }) => {
  const { tags, statistics, selectedTag, setSelectedTag, fetchTags } = useNewsStore()
  const [cardWidth, setCardWidth] = useState<number>(800)
  const [zoom, setZoom] = useState<number>(0.9)
  const [darkMode, setDarkMode] = useState(true)

  React.useEffect(() => {
    const event = new CustomEvent('card-width-change', { detail: cardWidth })
    window.dispatchEvent(event)
  }, [cardWidth])

  React.useEffect(() => {
    const event = new CustomEvent('zoom-change', { detail: zoom / 100 })
    window.dispatchEvent(event)
  }, [zoom])

  React.useEffect(() => {
    if (darkMode) {
      document.documentElement.removeAttribute('data-theme')
    } else {
      document.documentElement.setAttribute('data-theme', 'light')
    }
  }, [darkMode])

  React.useEffect(() => {
    if (tags.length === 0) fetchTags()
  }, [])

  const navItems = [
    { id: 'featured' as const, icon: '⚡', label: '精选情报' },
    { id: 'all' as const, icon: '📰', label: '全部事件' },
    { id: 'bookmarks' as const, icon: '⭐', label: '收藏夹' },
  ] as const

  return (
    <aside className="w-64 flex-shrink-0 border-r border-border-light bg-bg-secondary min-h-[calc(100vh-3.5rem)] overflow-y-auto">
      <nav className="p-4 space-y-6">
        <div>
          <div className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3 px-3">
            情报分类
          </div>
          <div className="space-y-1">
            {navItems.map(item => (
              <button
                key={item.id}
                onClick={() => {
                  onFilterChange(item.id)
                  setSelectedTag(null)
                }}
                className={clsx('w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors',
                  filter === item.id
                    ? 'bg-accent/10 text-accent border border-accent/20'
                    : 'text-text-secondary hover:bg-white/5 hover:text-text-primary'
                )}
              >
                <span className="text-lg">{item.icon}</span>
                <span className="font-medium">{item.label}</span>
              </button>
            ))}
          </div>
        </div>

        <div>
          <div className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3 px-3">
            信号标签
          </div>
          <div className="flex flex-wrap gap-2 px-3">
            {tags.slice(0, 20).map(tag => (
              <button
                key={tag}
                onClick={() => setSelectedTag(tag === selectedTag ? null : tag)}
                className={clsx(
                  'px-2.5 py-1 rounded-lg text-sm transition-colors border',
                  selectedTag === tag
                    ? 'bg-accent/10 border-accent/30 text-accent'
                    : 'bg-white/3 border-white/5 text-text-secondary hover:border-accent/30 hover:text-accent'
                )}
              >
                {tag}
              </button>
            ))}
          </div>
        </div>

        {/* 设置区域 */}
        <div className="pt-4 border-t border-border-light">
          <div className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3 px-3">
            显示设置
          </div>
          
          {/* 卡片宽度切换 */}
          <div className="px-3 mb-4">
            <div className="text-sm text-text-secondary mb-2">卡片宽度</div>
            <div className="flex bg-white/5 rounded-lg p-1 gap-1">
              {cardWidthOptions.map(opt => (
                <button
                  key={opt.value}
                  onClick={() => setCardWidth(opt.value)}
                  className={clsx(
                    'flex-1 py-1.5 text-xs font-medium rounded-md transition-all',
                    cardWidth === opt.value
                      ? 'bg-accent/20 text-accent shadow-sm'
                      : 'text-text-secondary hover:text-text-primary hover:bg-white/5'
                  )}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* 视图缩放切换 - 滑块 */}
          <div className="px-3 mb-4">
            <div className="text-sm text-text-secondary mb-2">视图缩放</div>
            <div className="px-2">
              <input
                type="range"
                min="90"
                max="150"
                step="1"
                value={zoom}
                onChange={(e) => setZoom(Number(e.target.value))}
                className="w-full h-2 bg-white/10 rounded-lg appearance-none cursor-pointer accent-accent"
              />
              <div className="flex justify-between mt-2 text-xs text-text-muted">
                <span>90%</span>
                <span className="text-accent font-semibold">{zoom}%</span>
                <span>150%</span>
              </div>
            </div>
          </div>

          {/* 深浅主题切换 */}
          <div className="px-3 mb-4">
            <div className="text-sm text-text-secondary mb-2">显示模式</div>
            <button
              onClick={() => setDarkMode(!darkMode)}
              className={clsx(
                'w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-colors',
                darkMode ? 'bg-accent/10 text-accent border border-accent/20' : 'bg-white/5 text-text-secondary'
              )}
            >
              <span>{darkMode ? '深色模式' : '浅色模式'}</span>
              <span className="text-lg">{darkMode ? '🌙' : '☀️'}</span>
            </button>
          </div>
        </div>

        {/* 统计信息 */}
        <div className="pt-4 border-t border-border-light px-3">
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-text-muted">总事件数</span>
              <span className="text-text-primary font-semibold">{statistics?.total_news || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-muted">AI 已分析</span>
              <span className="text-accent font-semibold">{statistics?.analyzed_news || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-muted">信号标签</span>
              <span className="text-text-secondary">{statistics?.total_tags || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-muted">收藏</span>
              <span className="text-text-secondary">{statistics?.total_bookmarks || '-'}</span>
            </div>
          </div>
        </div>
      </nav>
    </aside>
  )
}

export default Sidebar
