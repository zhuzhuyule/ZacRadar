import React from 'react'
import { NewsItem } from '../store/newsStore'

interface NewsCardProps {
  news: NewsItem
  onBookmark: (newsId: number) => Promise<void>
}

const NewsCard: React.FC<NewsCardProps> = ({ news, onBookmark }) => {
  return (
    <article className="timeline-card p-3 mb-2">
      {/* 第 1 行：来源信息 + 操作区 */}
      <div className="flex items-center justify-between mb-2">
        {/* 来源信息 - 一行展示 */}
        <div className="flex items-center gap-2 text-xs text-text-muted overflow-hidden">
          <span className="text-text-secondary font-medium truncate" title={news.platform_name}>
            {news.platform_name}
          </span>
          {news.url && (
            <>
              <span>·</span>
              <a
                href={news.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-accent hover:underline truncate"
              >
                原文
              </a>
            </>
          )}
          <span>·</span>
          <span className="truncate">#{news.rank}</span>
        </div>

        {/* 操作区：热度 + 收藏 */}
        <div className="flex items-center gap-2 flex-shrink-0">
          <span className={`score-badge ${news.ai_heat_score >= 85 ? 'high' : ''}`}>
            {news.ai_heat_score}
          </span>
          <button
            onClick={() => onBookmark(news.id)}
            className={`icon-btn-mini ${news.is_bookmarked ? 'active' : ''}`}
            title="收藏"
          >
            <svg className="w-4 h-4" fill={news.is_bookmarked ? 'currentColor' : 'none'} stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
            </svg>
          </button>
        </div>
      </div>

      {/* 第 2 行：标题 - 一行展示 */}
      <h2 className="text-sm font-semibold text-text-primary mb-2 truncate" title={news.title}>
        {news.title}
      </h2>

      {/* 第 3 行：简讯 - 可换行（2 行限制） */}
      {news.ai_reason && (
        <p className="text-xs text-text-secondary mb-2 leading-relaxed line-clamp-2">
          {news.ai_reason}
        </p>
      )}

      {/* 第 4 行：分类标签 + 数据来源 - 一行展示 */}
      <div className="flex items-center gap-1 mb-2 overflow-x-auto">
        {news.ai_tags.slice(0, 5).map((tag, i) => (
          <span key={i} className="tag-mini flex-shrink-0">
            {tag}
          </span>
        ))}
        {news.related_count > 0 && (
          <span className="aggregate-bar flex-shrink-0 ml-1">
            <span className="text-accent font-medium">{news.related_count}</span> 篇来源
          </span>
        )}
      </div>

      {/* 第 5 行：推荐理由 - 一行展示 */}
      {news.ai_heat_score >= 75 && (
        <div className="recommendation-bar">
          <span className="text-accent-green font-medium">推荐理由：</span>
          <span className="text-text-secondary truncate">{news.ai_reason}</span>
        </div>
      )}
    </article>
  )
}

export default NewsCard
