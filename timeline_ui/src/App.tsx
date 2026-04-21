import { useState, useEffect, useMemo } from 'react'
import { useNewsStore, NewsItem, Platform, TimelineEvent } from './store/newsStore'

/* ================= ICONS ================= */
const Icon = {
  feed: (p: any) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M4 11a9 9 0 0 1 9 9"/><path d="M4 4a16 16 0 0 1 16 16"/><circle cx="5" cy="19" r="1"/></svg>,
  grid: (p: any) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" {...p}><rect x="3" y="3" width="7" height="7" rx="1.2"/><rect x="14" y="3" width="7" height="7" rx="1.2"/><rect x="3" y="14" width="7" height="7" rx="1.2"/><rect x="14" y="14" width="7" height="7" rx="1.2"/></svg>,
  radar: (p: any) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" {...p}><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><path d="M12 12 L18 7"/></svg>,
  search: (p: any) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" {...p}><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>,
  bookmark: ({ filled, ...p }: { filled?: boolean } & any) => <svg viewBox="0 0 24 24" fill={filled ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M6 4h12v16l-6-4-6 4z"/></svg>,
  spark: (p: any) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M5.6 18.4l2.1-2.1M16.3 7.7l2.1-2.1"/></svg>,
  trend: (p: any) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="m3 17 6-6 4 4 8-8"/><path d="M14 7h7v7"/></svg>,
  link: (p: any) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M10 14a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-1 1"/><path d="M14 10a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l1-1"/></svg>,
  sliders: (p: any) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" {...p}><path d="M4 7h6M14 7h6M4 12h2M10 12h10M4 17h12M16 17h4"/><circle cx="12" cy="7" r="2"/><circle cx="8" cy="12" r="2"/><circle cx="14" cy="17" r="2"/></svg>,
}

/* ================= PLATFORM MARKS (brand SVGs, keyed by our real IDs) ================= */
const PLATFORM_MARKS: Record<string, JSX.Element> = {
  toutiao: (
    <svg viewBox="0 0 32 32"><rect width="32" height="32" rx="6" fill="#FA2A2D"/><path d="M8 9 L16 9 L14.5 13 L10.5 13 L8 23 L4 23 Z" fill="#fff" transform="translate(4)"/><path d="M20 9 L27 9 L25.8 12 L22 12 L20 23 L16 23 L18 12 L22.5 12 Z" fill="#fff" opacity="0.8" transform="translate(-1)"/></svg>
  ),
  baidu: (
    <svg viewBox="0 0 32 32"><rect width="32" height="32" rx="6" fill="#2932E1"/><ellipse cx="11" cy="11" rx="2.2" ry="3" fill="#fff"/><ellipse cx="18" cy="10" rx="2.2" ry="3.2" fill="#fff"/><ellipse cx="24" cy="13.5" rx="1.8" ry="2.6" fill="#fff"/><path d="M14 18 C11 18 9 20.5 9 23 C9 25 10.5 26 13 26 L20 26 C22.5 26 24 25 24 23 C24 20.5 22 18 19 18 Z" fill="#fff"/></svg>
  ),
  ifeng: (
    <svg viewBox="0 0 32 32"><rect width="32" height="32" rx="6" fill="#C4161C"/><path d="M7 20 C10 14 14 11 22 9 C18 13 18 15 21 16 C17 17 15 19 14 24 C12 21 10 21 7 20 Z" fill="#fff"/><circle cx="22" cy="22" r="2" fill="#FFD66E"/></svg>
  ),
  thepaper: (
    <svg viewBox="0 0 32 32"><rect width="32" height="32" rx="6" fill="#003D7C"/><rect x="7" y="8" width="18" height="16" fill="#fff"/><rect x="9" y="10" width="14" height="1.5" fill="#003D7C"/><rect x="9" y="13" width="6" height="6" fill="#003D7C"/><rect x="16" y="13" width="7" height="1" fill="#003D7C"/><rect x="16" y="15" width="7" height="1" fill="#003D7C"/><rect x="16" y="17" width="5" height="1" fill="#003D7C"/><rect x="9" y="20.5" width="14" height="1" fill="#003D7C"/></svg>
  ),
  zhihu: (
    <svg viewBox="0 0 32 32"><rect width="32" height="32" rx="6" fill="#056DE8"/><path d="M8 10 L20 10 L20 13 L13 13 L20 22 L16.5 22 L10 14 L10 24 L7 24 Z" fill="#fff"/><path d="M22 16 L26 16 L24 24 L22 22 Z" fill="#fff"/></svg>
  ),
  tieba: (
    <svg viewBox="0 0 32 32"><rect width="32" height="32" rx="6" fill="#4E6EF2"/><path d="M8 9 L22 9 L24 14 L16 14 L10 23 L8 20 Z" fill="#fff"/><circle cx="20" cy="20" r="3" fill="#fff"/></svg>
  ),
  weibo: (
    <svg viewBox="0 0 32 32"><rect width="32" height="32" rx="6" fill="#E6162D"/><ellipse cx="15" cy="17" rx="8" ry="6" fill="#fff"/><ellipse cx="13" cy="17" rx="3" ry="2.2" fill="#E6162D"/><circle cx="12.5" cy="16.5" r="1" fill="#fff"/><circle cx="23" cy="11" r="2.5" fill="#FFD66E"/></svg>
  ),
  douyin: (
    <svg viewBox="0 0 32 32"><rect width="32" height="32" rx="6" fill="#000"/><path d="M17 7 L17 20 C17 22 15.5 23 13.5 23 C11.5 23 10 22 10 20 C10 18 11.5 17 13.5 17 L13.5 13 C11 13 8 14.5 8 18 C8 22 11 25 14 25 C17 25 20 23 20 19 L20 12 C21.5 13.5 23 14 25 14 L25 10 C22.5 10 21 9 20 7 Z" fill="#25F4EE" transform="translate(-1,0)"/><path d="M17 7 L17 20 C17 22 15.5 23 13.5 23 C11.5 23 10 22 10 20 C10 18 11.5 17 13.5 17 L13.5 13 C11 13 8 14.5 8 18 C8 22 11 25 14 25 C17 25 20 23 20 19 L20 12 C21.5 13.5 23 14 25 14 L25 10 C22.5 10 21 9 20 7 Z" fill="#FE2C55" transform="translate(1,1)" opacity="0.9"/><path d="M17 7 L17 20 C17 22 15.5 23 13.5 23 C11.5 23 10 22 10 20 C10 18 11.5 17 13.5 17 L13.5 13 C11 13 8 14.5 8 18 C8 22 11 25 14 25 C17 25 20 23 20 19 L20 12 C21.5 13.5 23 14 25 14 L25 10 C22.5 10 21 9 20 7 Z" fill="#fff"/></svg>
  ),
  'bilibili-hot-search': (
    <svg viewBox="0 0 32 32"><rect width="32" height="32" rx="6" fill="#FB7299"/><path d="M10 8 L14 12 M22 8 L18 12" stroke="#fff" strokeWidth="1.8" strokeLinecap="round"/><rect x="7" y="12" width="18" height="12" rx="2.5" fill="#fff"/><circle cx="13" cy="18" r="1.4" fill="#FB7299"/><circle cx="19" cy="18" r="1.4" fill="#FB7299"/></svg>
  ),
  'wallstreetcn-hot': (
    <svg viewBox="0 0 32 32"><rect width="32" height="32" rx="6" fill="#000"/><text x="16" y="23" textAnchor="middle" fontFamily="Georgia, serif" fontSize="18" fontWeight="700" fill="#fff">WSJ</text></svg>
  ),
  'cls-hot': (
    <svg viewBox="0 0 32 32"><rect width="32" height="32" rx="6" fill="#E74C3C"/><path d="M7 22 L13 14 L17 18 L25 9" stroke="#fff" strokeWidth="2.4" fill="none" strokeLinecap="round" strokeLinejoin="round"/><path d="M20 9 L25 9 L25 14" stroke="#fff" strokeWidth="2.4" fill="none" strokeLinecap="round" strokeLinejoin="round"/></svg>
  ),
  'rss:hacker-news': (
    <svg viewBox="0 0 32 32"><rect width="32" height="32" rx="6" fill="#FF6600"/><text x="16" y="22" textAnchor="middle" fontFamily="Verdana, sans-serif" fontSize="16" fontWeight="700" fill="#fff">Y</text></svg>
  ),
  'rss:yahoo-finance': (
    <svg viewBox="0 0 32 32"><rect width="32" height="32" rx="6" fill="#720E9E"/><text x="16" y="22" textAnchor="middle" fontFamily="Helvetica, sans-serif" fontSize="16" fontWeight="800" fill="#fff">Y!</text></svg>
  ),
}

/* 时间格式化：优先用 ms 时间戳（真实平台 updatedTime / RSS published_at），
   回退到"HH-MM"字符串改成"HH:MM"避免被误读成日期 */
function fmtHM(tsMs?: number | null, fallback?: string | null): string {
  if (tsMs && tsMs > 0) {
    const d = new Date(tsMs)
    return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
  }
  const s = (fallback || '').trim()
  const m = s.match(/^(\d{1,2})[-:：](\d{2})$/)
  if (m) return `${m[1].padStart(2, '0')}:${m[2]}`
  return s
}

function PlatformAvatar({ p, size = 22 }: { p?: Platform; size?: number }) {
  if (!p) return null
  const mark = PLATFORM_MARKS[p.id]
  return (
    <span className="plat-avatar brand" style={{ width: size, height: size }} title={p.name}>
      {mark || (
        <span style={{ background: p.color, width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontSize: size * 0.5, fontWeight: 600, borderRadius: 'inherit' }}>
          {p.name[0]}
        </span>
      )}
    </span>
  )
}

function PlatformStack({ platforms, max = 5 }: { platforms: Platform[]; max?: number }) {
  const [open, setOpen] = useState(false)
  const shown = platforms.slice(0, max)
  const more = platforms.length - shown.length
  return (
    <div className="plat-stack-wrap" onMouseEnter={() => setOpen(true)} onMouseLeave={() => setOpen(false)}>
      <div className="plat-stack">
        {shown.map(p => <PlatformAvatar key={p.id} p={p}/>)}
        {more > 0 && (
          <span className="plat-avatar more" style={{ width: 22, height: 22, fontSize: 10 }}>+{more}</span>
        )}
      </div>
      {open && (
        <div className="plat-popover">
          <div className="plat-popover-title">
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--fg-mute)', letterSpacing: '0.1em', textTransform: 'uppercase' }}>{platforms.length} 个平台同报</span>
          </div>
          <div className="plat-popover-list">
            {platforms.map(p => (
              <div key={p.id} className="plat-popover-row">
                <PlatformAvatar p={p} size={18}/>
                <span>{p.name}</span>
                <span style={{ marginLeft: 'auto', fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--fg-mute)' }}>{p.category}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

/* ================= TOPBAR ================= */
function Topbar({ view, setView, search, setSearch, onTweaks, isMobile }: any) {
  return (
    <header className="topbar">
      <div className="brand">
        <span className="brand-mark" aria-hidden="true"/>
        <span className="full">RADAR</span>
      </div>
      {!isMobile && (
        <div className="view-tabs" role="tablist">
          <button data-active={view === 'home'} onClick={() => setView('home')}><Icon.radar/>主页</button>
          <button data-active={view === 'feed'} onClick={() => setView('feed')}><Icon.feed/>关注 Feed</button>
          <button data-active={view === 'platforms'} onClick={() => setView('platforms')}><Icon.grid/>平台榜</button>
          <button data-active={view === 'bookmarks'} onClick={() => setView('bookmarks')}><Icon.bookmark/>收藏</button>
        </div>
      )}
      <div className="spacer"/>
      <div className="search">
        <Icon.search className="search-icon" style={{ width: 14, height: 14 }}/>
        <input placeholder="搜索标题 / 标签 / 推荐理由" value={search} onChange={e => setSearch(e.target.value)}/>
        <span className="kbd">⌘K</span>
      </div>
      <span className="live-dot"><span className="pulse"/>LIVE</span>
      <button className="pill" onClick={onTweaks} title="Tweaks" style={{ padding: '6px 10px' }}>
        <Icon.sliders style={{ width: 14, height: 14 }}/>
      </button>
    </header>
  )
}

/* ================= SIDEBAR ================= */
function Sidebar({ platformFilter, setPlatformFilter, interestFilter, setInterestFilter }: any) {
  const { platforms, interests, news } = useNewsStore()
  return (
    <aside className="sidebar">
      <div className="sidebar-section">
        <div className="sidebar-label">平台 <span className="count">{platforms.length}</span></div>
        <div className="platform-row" data-active={!platformFilter} onClick={() => setPlatformFilter(null)}
             style={!platformFilter ? { background: 'var(--bg-elev-2)', color: 'var(--fg)' } : undefined}>
          <span className="platform-dot" style={{ background: 'var(--fg-dim)' }}/>
          <span>全部平台</span>
          <span className="count">{news.length}</span>
        </div>
        {platforms.map(p => (
          <div key={p.id} className="platform-row"
               style={platformFilter === p.id ? { background: 'var(--bg-elev-2)', color: 'var(--fg)' } : undefined}
               onClick={() => setPlatformFilter(platformFilter === p.id ? null : p.id)}>
            <PlatformAvatar p={p} size={16}/>
            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{p.name}</span>
            <span className="count">{p.news_count}</span>
          </div>
        ))}
      </div>
      <div className="sidebar-section">
        <div className="sidebar-label">兴趣方向 <span className="count">{interests.length}</span></div>
        {interests.slice(0, 10).map(it => (
          <div key={it.id} className="interest-row"
               style={interestFilter === it.id ? { background: 'var(--bg-elev-2)', color: 'var(--fg)' } : undefined}
               onClick={() => setInterestFilter(interestFilter === it.id ? null : it.id)}>
            <span className="priority" data-p={it.priority}>P{it.priority}</span>
            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{it.tag}</span>
            <span className="count">{it.hits}</span>
          </div>
        ))}
      </div>
    </aside>
  )
}

/* ================= EVENT CARD ================= */
function EventCard({ event, primary, onOpen }: { event: TimelineEvent; primary?: boolean; onOpen?: (e: TimelineEvent) => void }) {
  const { platforms } = useNewsStore()
  const pmap = new Map(platforms.map(p => [p.id, p]))
  const platformObjs = event.platform_ids.map(id => pmap.get(id)).filter(Boolean) as Platform[]
  return (
    <div className={`event-card ${primary ? 'primary' : ''}`} onClick={() => onOpen && onOpen(event)}>
      <div className="event-header">
        <span className="badge"><Icon.link style={{ width: 12, height: 12 }}/>{event.news_count} 条同报</span>
        <span style={{ opacity: 0.5 }}>·</span>
        <span>EVT-{event.event_id}</span>
        {event.rising && (<>
          <span style={{ opacity: 0.5 }}>·</span>
          <span className="rising"><Icon.trend style={{ width: 12, height: 12 }}/>RISING</span>
        </>)}
      </div>
      <h3 className="event-title">{event.event_name}</h3>
      {primary && event.summary && event.summary !== event.event_name && <p className="event-summary">{event.summary}</p>}
      <div className="event-footer">
        <PlatformStack platforms={platformObjs} max={primary ? 6 : 4}/>
        <div className="heat-bar">
          <span>热度 {event.heat}</span>
          <div className="meter"><div className="fill" style={{ width: event.heat + '%' }}/></div>
        </div>
      </div>
    </div>
  )
}

/* ================= NEWS ROW ================= */
function NewsRow({ item, showReason, eventName }: { item: NewsItem; showReason: boolean; eventName?: string }) {
  const { bookmarks, toggleBookmark } = useNewsStore()
  const isBookmarked = bookmarks.has(item.id)
  const scoreClass = item.personal_score >= 90 ? 'super' : item.personal_score >= 75 ? 'hi' : ''
  const platShort = item.platform_id.replace('rss:', '').replace('-hot', '').replace('-hot-search', '').slice(0, 3).toUpperCase()
  const tags = item.tags || item.ai_tags || []
  const openOriginal = () => { if (item.url) window.open(item.url, '_blank', 'noopener,noreferrer') }
  return (
    <div className="news-row" onClick={openOriginal} role={item.url ? 'link' : undefined} tabIndex={item.url ? 0 : undefined}
         onKeyDown={e => { if ((e.key === 'Enter' || e.key === ' ') && item.url) { e.preventDefault(); openOriginal() } }}>
      <div className="news-rank" title={`在 ${item.platform_name} 原榜单上排第 ${item.rank} 位`}>
        <span style={{ fontWeight: 600 }}>{item.rank}</span>
        <span className="plat" style={{ color: item.platform_color }}>{platShort}</span>
      </div>
      <div className="news-body">
        <div className="news-title">
          {eventName && (
            <span className="hot-event-tag" title={`热点事件：${eventName}`}>
              <Icon.radar style={{ width: 10, height: 10 }}/>热点
            </span>
          )}
          {item.title_zh && item.title_zh !== item.title ? item.title_zh : item.title}
          {item.title_zh && item.title_zh !== item.title && <span className="alt">{item.title}</span>}
        </div>
        {item.description ? (
          <div className="news-desc">{item.description}</div>
        ) : item.ai_reason ? (
          <div className="news-desc news-desc-ai">
            <span className="ai-prefix">AI ·</span> {item.ai_reason}
          </div>
        ) : null}
        <div className="news-meta">
          <span className="platform">
            <PlatformAvatar p={{ id: item.platform_id, name: item.platform_name, color: item.platform_color || '#888', category: item.platform_category, news_count: 0, latest_updated_ts: 0, latest_crawl_time: '' } as Platform} size={12}/>
            {item.platform_name}
          </span>
          <span className="sep">·</span>
          <span title={item.source_updated_ts ? new Date(item.source_updated_ts).toLocaleString('zh-CN') : ''}>
            {item.platform_id.startsWith('rss:') ? '发布 ' : '榜单 '}{fmtHM(item.source_updated_ts, item.first_crawl_time)}
          </span>
          {item.crawl_count >= 3 && (<><span className="sep">·</span><span>持续 ×{item.crawl_count}</span></>)}
          {item.related_count > 0 && (<><span className="sep">·</span><span className="related"><Icon.link style={{ width: 10, height: 10 }}/>{item.related_count} 平台</span></>)}
          {item.hot_value && (<><span className="sep">·</span><span className="hot">🔥 {item.hot_value}</span></>)}
          {Array.from(new Set(tags.filter(Boolean))).slice(0, 3).map(t => <span key={t} className="tag">{t}</span>)}
          {item.url && (<>
            <span className="sep">·</span>
            <a href={item.url} target="_blank" rel="noopener noreferrer"
               className="origin-link" onClick={e => e.stopPropagation()}>原文 ↗</a>
          </>)}
        </div>
        {/* 仅当有原文摘要 && 单独启用推荐理由时，再显示绿色 AI bar，避免重复 */}
        {showReason && item.ai_reason && item.description && (
          <div className="ai-reason">
            <span className="tag-lbl">AI</span>
            <span>{item.ai_reason}</span>
          </div>
        )}
      </div>
      <div className="news-aside">
        <span className={`score-chip ${scoreClass}`}><Icon.spark style={{ width: 10, height: 10 }}/>{item.personal_score}</span>
        <button className="bookmark-btn" data-on={isBookmarked} onClick={e => { e.stopPropagation(); toggleBookmark(item.id) }}>
          <Icon.bookmark filled={isBookmarked} style={{ width: 16, height: 16 }}/>
        </button>
      </div>
    </div>
  )
}

/* ================= NEWS CARD (Feed grid) ================= */
function NewsCard({ item, showReason, eventName }: { item: NewsItem; showReason: boolean; eventName?: string }) {
  const { bookmarks, toggleBookmark } = useNewsStore()
  const isBookmarked = bookmarks.has(item.id)
  const scoreClass = item.personal_score >= 90 ? 'super' : item.personal_score >= 75 ? 'hi' : ''
  const tags = item.tags || item.ai_tags || []
  const openOriginal = () => { if (item.url) window.open(item.url, '_blank', 'noopener,noreferrer') }
  const platformObj = { id: item.platform_id, name: item.platform_name, color: item.platform_color || '#888', category: item.platform_category, news_count: 0, latest_updated_ts: 0, latest_crawl_time: '' } as Platform
  return (
    <article className="news-card" onClick={openOriginal} role={item.url ? 'link' : undefined} tabIndex={item.url ? 0 : undefined}
             onKeyDown={e => { if ((e.key === 'Enter' || e.key === ' ') && item.url) { e.preventDefault(); openOriginal() } }}>
      <div className="nc-left">
        {item.icon_url ? (
          <img src={item.icon_url} alt="" className="nc-thumb" loading="lazy"
               onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none' }}/>
        ) : (
          <PlatformAvatar p={platformObj} size={40}/>
        )}
        <span className="nc-col" title={`榜单：${item.platform_name}`}>{item.platform_name}</span>
      </div>
      <div className="nc-main">
        <h3 className="nc-title">
          <span className="nc-title-text">
            {item.title_zh && item.title_zh !== item.title ? item.title_zh : item.title}
          </span>
          {eventName && (
            <span className="hot-event-tag" title={`热点事件：${eventName}`}>
              <Icon.radar style={{ width: 10, height: 10 }}/>热点
            </span>
          )}
        </h3>
        {item.title_zh && item.title_zh !== item.title && <div className="nc-alt">{item.title}</div>}
        {item.description ? (
          <p className="nc-desc">{item.description}</p>
        ) : item.ai_reason ? (
          <p className="nc-desc nc-desc-ai"><span className="ai-prefix">AI ·</span> {item.ai_reason}</p>
        ) : null}
        {showReason && item.ai_reason && item.description && (
          <div className="ai-reason">
            <span className="tag-lbl">AI</span><span>{item.ai_reason}</span>
          </div>
        )}
        <div className="news-card-foot">
          <span className="nc-time" title={item.source_updated_ts ? new Date(item.source_updated_ts).toLocaleString('zh-CN') : ''}>
            {item.platform_id.startsWith('rss:') ? '发布 ' : '榜单 '}{fmtHM(item.source_updated_ts, item.first_crawl_time)}
          </span>
          {item.related_count > 0 && (<><span className="sep">·</span><span className="nc-related"><Icon.link style={{ width: 10, height: 10 }}/>{item.related_count} 平台</span></>)}
          {item.hot_value && (<><span className="sep">·</span><span className="nc-hot">🔥 {item.hot_value}</span></>)}
          {Array.from(new Set(tags.filter(Boolean))).slice(0, 3).map(t => <span key={t} className="tag">{t}</span>)}
        </div>
      </div>
      <div className="nc-aside">
        <button className="bookmark-btn" data-on={isBookmarked} onClick={e => { e.stopPropagation(); toggleBookmark(item.id) }}>
          <Icon.bookmark filled={isBookmarked} style={{ width: 15, height: 15 }}/>
        </button>
        <span className={`score-chip ${scoreClass}`}>
          <Icon.spark style={{ width: 10, height: 10 }}/>{item.personal_score}
        </span>
      </div>
    </article>
  )
}

/* ================= RIGHTBAR ================= */
function Rightbar({ activeTag, setActiveTag, interestFilter, setInterestFilter, platformFilter, setPlatformFilter, setView }: any) {
  const { news, platforms, interests, statistics } = useNewsStore()
  const goFeedWith = (fn: () => void) => { fn(); setView && setView('feed') }
  const topTags = useMemo(() => {
    const counts: Record<string, number> = {}
    news.forEach(n => (n.tags || n.ai_tags || []).forEach(t => { counts[t] = (counts[t] || 0) + 1 }))
    return Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 14)
  }, [news])

  const platformPulse = useMemo(() => {
    return platforms.map(p => {
      const items = news.filter(n => n.platform_id === p.id)
      const avg = items.reduce((s, n) => s + (n.ai_heat_score || 0), 0) / Math.max(1, items.length)
      return { ...p, avg, count: items.length }
    }).sort((a, b) => b.avg - a.avg).slice(0, 8)
  }, [news, platforms])

  return (
    <aside className="rightbar">
      <div className="rb-section">
        <div className="label">今日概览</div>
        <div className="rb-stat-grid">
          <div className="rb-stat"><div className="v">{statistics?.total || 0}</div><div className="k">Total</div></div>
          <div className="rb-stat"><div className="v">{statistics?.events || 0}</div><div className="k">Events</div></div>
          <div className="rb-stat"><div className="v">{statistics?.heat_ge_80 || 0}</div><div className="k">Hot ≥80</div></div>
          <div className="rb-stat"><div className="v">{statistics ? Math.round((statistics.analyzed / Math.max(1, statistics.total)) * 100) : 0}<span style={{ fontSize: 14 }}>%</span></div><div className="k">Analyzed</div></div>
        </div>
      </div>
      <div className="rb-section">
        <div className="label">平台热度脉冲</div>
        <div className="pulse-list">
          {platformPulse.map(p => {
            const on = platformFilter === p.id
            return (
              <div key={p.id} className="pulse-row clickable" data-active={on}
                   title={on ? '取消筛选' : `在 Feed 中筛选 ${p.name}`}
                   onClick={() => goFeedWith(() => setPlatformFilter && setPlatformFilter(on ? null : p.id))}>
                <span className="name" style={{ color: p.color }}>{p.name}</span>
                <div className="bar"><div className="fill" style={{ width: p.avg + '%', background: p.color }}/></div>
                <span className="v">{Math.round(p.avg)}</span>
              </div>
            )
          })}
        </div>
      </div>
      <div className="rb-section">
        <div className="label">高频标签</div>
        <div className="rb-tags">
          {topTags.filter(([t]) => t).map(([t, n]) => {
            const on = activeTag === t
            return (
              <button key={t as string} className="rb-tag clickable" data-active={on}
                      title={on ? '取消标签筛选' : `在 Feed 中按 #${t} 筛选`}
                      onClick={() => goFeedWith(() => setActiveTag && setActiveTag(on ? null : t))}>
                {t}<span className="n">{n}</span>
              </button>
            )
          })}
        </div>
      </div>
      <div className="rb-section">
        <div className="label">兴趣命中 TOP 5</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          {interests.slice(0, 5).map(it => {
            const on = interestFilter === it.id
            return (
              <button key={it.id} className="rb-interest-row clickable" data-active={on}
                      title={on ? '取消兴趣筛选' : `在 Feed 中按「${it.tag}」筛选`}
                      onClick={() => goFeedWith(() => setInterestFilter && setInterestFilter(on ? null : it.id))}>
                <span className="t">{it.tag}</span>
                <span className="h">{it.hits}</span>
              </button>
            )
          })}
        </div>
      </div>
    </aside>
  )
}

/* ================= DEV: FORCE CRAWL ================= */
function DevCrawlRow() {
  const base = (import.meta as any).env?.DEV ? 'http://localhost:8001/api/timeline' : '/api/timeline'
  const [busy, setBusy] = useState(false)
  const [status, setStatus] = useState<any>(null)

  const poll = async () => {
    try {
      const r = await fetch(`${base}/crawl/status`).then(r => r.json())
      setStatus(r.data)
      if (r.data?.running) setTimeout(poll, 1500)
      else setBusy(false)
    } catch { setBusy(false) }
  }

  const trigger = async () => {
    setBusy(true)
    try {
      const r = await fetch(`${base}/crawl`, { method: 'POST' }).then(r => r.json())
      if (r.status === 'running' || r.status === 'started') poll()
      else setBusy(false)
    } catch { setBusy(false) }
  }

  const rc = status?.rc
  const label = busy || status?.running ? '抓取中…'
    : rc === 0 ? `上次成功 · ${status?.finished_at ? new Date(status.finished_at * 1000).toLocaleTimeString('zh-CN') : ''}`
    : rc != null ? `rc=${rc}`
    : '未运行'

  return (
    <div className="tweak-row">
      <span className="lbl" style={{ color: 'var(--accent-warm)' }}>DEV · 强制抓取</span>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--fg-mute)' }}>
        <button className="pill" onClick={trigger} disabled={busy || status?.running}
                style={{ fontSize: 11, opacity: busy || status?.running ? 0.5 : 1 }}>
          触发一次
        </button>
        <span>{label}</span>
      </div>
    </div>
  )
}

/* ================= TWEAKS ================= */
function TweaksPanel({ open, onClose, theme, setTheme, density, setDensity, showReason, setShowReason, heroStyle, setHeroStyle, layout, setLayout, lastRefresh, streamOn, onRefreshNow }: any) {
  return (
    <div className="tweaks-panel" data-open={open}>
      <h3>
        <span>TWEAKS</span>
        <button onClick={onClose} style={{ color: 'var(--fg-mute)', fontSize: 14 }}>✕</button>
      </h3>
      <div className="tweak-row">
        <span className="lbl">布局</span>
        <div className="seg">
          <button data-on={layout === 'standard'} onClick={() => setLayout('standard')}>标准</button>
          <button data-on={layout === 'minimal'} onClick={() => setLayout('minimal')}>简洁</button>
          <button data-on={layout === 'briefing'} onClick={() => setLayout('briefing')}>简报</button>
        </div>
      </div>
      <div className="tweak-row">
        <span className="lbl">实时推送</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--fg-mute)' }}>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>
            <span style={{ width: 7, height: 7, borderRadius: '50%', background: streamOn ? 'var(--accent-green)' : 'var(--fg-mute)' }}/>
            {streamOn ? '已连接' : '未连接'}
          </span>
          <span>· 上次 {lastRefresh ? new Date(lastRefresh).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '—'}</span>
          <button className="pill" onClick={onRefreshNow} style={{ fontSize: 11 }}>立即刷新</button>
        </div>
      </div>
      {(import.meta as any).env?.DEV && <DevCrawlRow/>}
      <div className="tweak-row">
        <span className="lbl">主题</span>
        <div className="seg">
          <button data-on={theme === 'dark'} onClick={() => setTheme('dark')}>深色</button>
          <button data-on={theme === 'light'} onClick={() => setTheme('light')}>浅色</button>
        </div>
      </div>
      <div className="tweak-row">
        <span className="lbl">密度</span>
        <div className="seg">
          <button data-on={density === 'compact'} onClick={() => setDensity('compact')}>紧凑</button>
          <button data-on={density === 'normal'} onClick={() => setDensity('normal')}>标准</button>
          <button data-on={density === 'roomy'} onClick={() => setDensity('roomy')}>宽松</button>
        </div>
      </div>
      <div className="tweak-row">
        <span className="lbl">AI 推荐理由</span>
        <div className="seg">
          <button data-on={!showReason} onClick={() => setShowReason(false)}>隐藏</button>
          <button data-on={showReason} onClick={() => setShowReason(true)}>展开</button>
        </div>
      </div>
      <div className="tweak-row">
        <span className="lbl">事件展示</span>
        <div className="seg">
          <button data-on={heroStyle === 'cards'} onClick={() => setHeroStyle('cards')}>卡片</button>
          <button data-on={heroStyle === 'band'} onClick={() => setHeroStyle('band')}>条带</button>
        </div>
      </div>
    </div>
  )
}

/* ================= VIEWS ================= */
function FeedView({ filters, showReason }: any) {
  const { news, events, interests } = useNewsStore()
  const { platformFilter, interestFilter, search, sortBy, activeTag } = filters
  const eventById = useMemo(() => new Map(events.map(e => [e.event_id, e])), [events])

  const activeInterest = useMemo(
    () => interests.find(it => it.id === interestFilter),
    [interests, interestFilter]
  )

  const filteredNews = useMemo(() => {
    let list = [...news]
    if (platformFilter) list = list.filter(n => n.platform_id === platformFilter)
    if (activeInterest) {
      list = list.filter(n =>
        (n.matched_interests || []).some(mi => mi.tag === activeInterest.tag)
        || n.primary_interest === activeInterest.tag
      )
    }
    if (search) {
      const q = search.toLowerCase()
      list = list.filter(n => (n.title + (n.title_zh || '') + (n.ai_reason || '') + (n.tags || n.ai_tags || []).join(' ')).toLowerCase().includes(q))
    }
    if (activeTag) list = list.filter(n => (n.tags || n.ai_tags || []).includes(activeTag))
    if (sortBy === 'heat') list.sort((a, b) => (b.ai_heat_score || 0) - (a.ai_heat_score || 0))
    else if (sortBy === 'time') list.sort((a, b) => (b.source_updated_ts || 0) - (a.source_updated_ts || 0))
    else list.sort((a, b) => (b.personal_score || 0) - (a.personal_score || 0))
    return list
  }, [news, platformFilter, activeInterest, search, sortBy, activeTag])

  return (
    <>
      <div className="section-head sticky">
        <h2>{
          activeTag ? `# ${activeTag}`
          : activeInterest ? `🎯 ${activeInterest.tag}`
          : platformFilter ? (useNewsStore.getState().platforms.find(p => p.id === platformFilter)?.name || '')
          : '精选信息流'
        }</h2>
        <span className="meta" title="综合分 = 0.6×兴趣相关 + 0.15×AI 热度 + 0.15×跨平台关联 + 0.1×平台权重">
          {filteredNews.length} 条 · {sortBy === 'personal' ? '按综合分排序（兴趣 60% + 热度 15% + 关联 15% + 平台 10%）' : sortBy === 'heat' ? '按 AI 热度排序' : '按首发时间排序'}
        </span>
      </div>
      <div className="news-grid">
        {filteredNews.map(item => <NewsCard key={item.id} item={item} showReason={showReason} eventName={item.event_id ? eventById.get(item.event_id)?.event_name : undefined}/>)}
      </div>
    </>
  )
}

function HomeView({ onOpenEvent }: any) {
  const { events, news, statistics } = useNewsStore()
  const [sortMode, setSortMode] = useState<'time' | 'heat' | 'count'>('time')
  const heroEvents = useMemo(() => [...events].sort((a, b) => (b.heat || 0) - (a.heat || 0)).slice(0, 5), [events])
  const [primary, ...restHero] = heroEvents
  const enriched = useMemo(() => {
    const rows = events.map(evt => {
      const items = news.filter(n => n.event_id === evt.event_id)
      const tsList = items.map(n => n.source_updated_ts || 0).filter(t => t > 0)
      const earliestTs = tsList.length ? Math.min(...tsList) : 0
      const latestTs = tsList.length ? Math.max(...tsList) : 0
      const aiComment = items.find(n => n.ai_reason)?.ai_reason || evt.rep_title || ''
      return { evt, items, earliestTs, latestTs, aiComment, heat: evt.heat || 0, count: items.length }
    })
    const cmp = (a: typeof rows[0], b: typeof rows[0]) => {
      if (sortMode === 'time') {
        return (a.earliestTs || Infinity) - (b.earliestTs || Infinity)
          || (b.heat - a.heat)
      }
      if (sortMode === 'heat') {
        return (b.heat - a.heat) || ((b.earliestTs || 0) - (a.earliestTs || 0))
      }
      return (b.count - a.count) || (b.heat - a.heat)
    }
    return rows.sort(cmp)
  }, [events, news, sortMode])
  const subHint = sortMode === 'time' ? '按首报时间由早至晚' : sortMode === 'heat' ? '按综合热度排序' : '按同报数量排序'
  return (
    <>
      <div className="page-header">
        <div>
          <h1>今天发生了什么</h1>
          <div className="sub">
            <span className="hl">{events.length}</span> 个跨平台事件 ·
            <span className="hl"> {statistics?.total || 0}</span> 条原始报道 ·
            AI 聚合分析
          </div>
        </div>
        <div style={{ color: 'var(--fg-mute)', fontFamily: 'var(--font-mono)', fontSize: 11 }}>
          {new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' })}
        </div>
      </div>
      {primary && (
        <>
          <div className="section-head">
            <h2>热点聚焦</h2>
            <span className="meta">跨平台共振 TOP {heroEvents.length}</span>
          </div>
          <div className="events-band">
            <EventCard event={primary} primary onOpen={onOpenEvent}/>
            {restHero.map(e => <EventCard key={e.event_id} event={e} onOpen={onOpenEvent}/>)}
          </div>
        </>
      )}
      <div className="section-head sticky" style={{ marginTop: 28 }}>
        <h2>事件时间线</h2>
        <span className="meta">{subHint}</span>
        <div className="seg" style={{ marginLeft: 'auto' }}>
          <button data-on={sortMode === 'time'} onClick={() => setSortMode('time')}>时间</button>
          <button data-on={sortMode === 'heat'} onClick={() => setSortMode('heat')}>热度</button>
          <button data-on={sortMode === 'count'} onClick={() => setSortMode('count')}>热点</button>
        </div>
      </div>
      <div className="events-timeline">
        {enriched.map(({ evt, items, earliestTs, aiComment, heat, count }) => (
          <div key={evt.event_id} className="events-timeline-item">
            <div className="events-timeline-time">
              {sortMode === 'time' && <>
                <span className="hm">{fmtHM(earliestTs, '')}</span>
                <span className="n">首报</span>
              </>}
              {sortMode === 'heat' && <>
                <span className="hm">{heat}</span>
                <span className="n">HEAT</span>
              </>}
              {sortMode === 'count' && <>
                <span className="hm">{count}</span>
                <span className="n">同报</span>
              </>}
            </div>
            <div className="events-timeline-rail"><span className="dot"/></div>
            <div className="events-timeline-body">
              <EventCard event={evt} primary onOpen={onOpenEvent}/>
              {aiComment && (
                <div className="event-ai-comment" onClick={() => onOpenEvent && onOpenEvent(evt)}>
                  <span className="tag-lbl">AI</span>
                  <span>{aiComment}</span>
                </div>
              )}
              <div className="event-open-hint" onClick={() => onOpenEvent && onOpenEvent(evt)}>
                查看 {items.length} 条原始报道 →
              </div>
            </div>
          </div>
        ))}
      </div>
    </>
  )
}

function PlatformsView({ onGoToFeed }: { onGoToFeed: (platformId: string) => void }) {
  const { platforms, news } = useNewsStore()
  return (
    <>
      <div className="page-header">
        <div>
          <h1>平台榜单</h1>
          <div className="sub">{platforms.length} 个平台的此刻热榜 · 统一时间轴对比</div>
        </div>
      </div>
      <div className="platforms-grid">
        {platforms.map(p => {
          const items = news.filter(n => n.platform_id === p.id).slice(0, 5)
          return (
            <div key={p.id} className="platform-card">
              <div className="platform-card-head">
                <div className="name"><PlatformAvatar p={p} size={22}/>{p.name}</div>
                <div className="meta">{p.category} · 更新 {fmtHM(p.latest_updated_ts, p.latest_crawl_time)}</div>
              </div>
              {items.length === 0 ? (
                <div style={{ color: 'var(--fg-mute)', fontSize: 12, padding: '6px 0' }}>暂无数据展示</div>
              ) : (
                <ul className="mini-list">
                  {items.map((n, i) => (
                    <li key={n.id} className="mini-item"
                        onClick={() => n.url && window.open(n.url, '_blank', 'noopener,noreferrer')}
                        title={n.url ? '点击打开原文' : ''}>
                      <span className="rk">#{i + 1}</span>
                      <span className="t">
                        {n.title_zh && n.title_zh !== n.title ? n.title_zh : n.title}
                        {n.hot_value && <span style={{ color: 'var(--accent-warm)', fontSize: 11, marginLeft: 6, fontFamily: 'var(--font-mono)' }}>{n.hot_value}</span>}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
              <div className="platform-card-foot" onClick={() => onGoToFeed(p.id)} title={`在 Feed 中筛选 ${p.name}`}>
                <span>{p.news_count} 条在榜</span>
                <span>查看全部 →</span>
              </div>
            </div>
          )
        })}
      </div>
    </>
  )
}

function BookmarksView({ showReason }: any) {
  const { news, bookmarks } = useNewsStore()
  const items = news.filter(n => bookmarks.has(n.id))
  return (
    <>
      <div className="page-header">
        <div>
          <h1>我的收藏</h1>
          <div className="sub">{items.length} 条 · 点击右侧 <Icon.bookmark style={{ width: 11, height: 11, verticalAlign: '-1px' }}/> 取消收藏</div>
        </div>
      </div>
      {items.length === 0 ? (
        <div style={{ textAlign: 'center', color: 'var(--fg-mute)', padding: '80px 20px', fontSize: 14 }}>
          <div style={{ fontSize: 40, marginBottom: 14, opacity: 0.4 }}>◈</div>
          还没有收藏的内容。在任意新闻条目右侧点击 <Icon.bookmark style={{ width: 14, height: 14, verticalAlign: '-2px' }}/> 即可加入收藏。
        </div>
      ) : (
        <div className="news-list">
          {items.map(item => <NewsRow key={item.id} item={item} showReason={showReason}/>)}
        </div>
      )}
    </>
  )
}

function BriefingView() {
  const { events, news, platforms, statistics } = useNewsStore()
  const pmap = new Map(platforms.map(p => [p.id, p]))
  return (
    <>
      <div className="briefing-hero">
        <div className="eyebrow">RADAR · DAILY BRIEFING</div>
        <h1>今天值得花 3 分钟看的 {events.length} 件事</h1>
        <div className="sub">
          {new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' })} · 截至 {statistics?.last_updated} · 覆盖 {platforms.length} 个平台
        </div>
      </div>
      <div className="briefing-list">
        {events.map((evt, i) => {
          const items = news.filter(n => n.event_id === evt.event_id)
          const platformObjs = evt.platform_ids.map(id => pmap.get(id)).filter(Boolean) as Platform[]
          return (
            <div key={evt.event_id} className="briefing-item">
              <div className="num">{String(i + 1).padStart(2, '0')}</div>
              <div>
                <h2>{evt.event_name}</h2>
                {evt.summary && evt.summary !== evt.event_name && <p>{evt.summary}</p>}
                <div className="sources">
                  {platformObjs.map(p => (
                    <span key={p.id} className="platform-chip"><span className="dot" style={{ background: p.color }}/>{p.name}</span>
                  ))}
                  <span className="platform-chip more">{items.length} 条 · 热度 {evt.heat}</span>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </>
  )
}

/* ================= EVENT DRAWER ================= */
function EventDrawer({ event, onClose }: { event: TimelineEvent | null; onClose: () => void }) {
  const { news, platforms, bookmarks, toggleBookmark } = useNewsStore()
  useEffect(() => {
    const onEsc = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', onEsc)
    return () => document.removeEventListener('keydown', onEsc)
  }, [onClose])
  if (!event) return null
  const items = news.filter(n => n.event_id === event.event_id)
  const pmap = new Map(platforms.map(p => [p.id, p]))
  const platformObjs = event.platform_ids.map(id => pmap.get(id)).filter(Boolean) as Platform[]
  const byPlat: Record<string, NewsItem[]> = {}
  items.forEach(n => { (byPlat[n.platform_id] = byPlat[n.platform_id] || []).push(n) })
  const sortedTimeline = [...items].sort((a, b) => (a.first_crawl_time || '').localeCompare(b.first_crawl_time || ''))
  return (
    <>
      <div className="drawer-scrim" onClick={onClose}/>
      <aside className="event-drawer">
        <header className="drawer-head">
          <div className="drawer-head-top">
            <span className="drawer-eyebrow">
              <Icon.link style={{ width: 12, height: 12 }}/> 跨平台事件 · EVT-{event.event_id}
              {event.rising && <> <span style={{ color: 'var(--accent-warm)', marginLeft: 8 }}>↑ RISING</span></>}
            </span>
            <button className="drawer-close" onClick={onClose} aria-label="关闭">✕</button>
          </div>
          <h2 className="drawer-title">{event.event_name}</h2>
          {event.summary && event.summary !== event.event_name && <p className="drawer-summary">{event.summary}</p>}
          <div className="drawer-stats">
            <div><span className="v">{items.length}</span><span className="k">条同报</span></div>
            <div><span className="v">{platformObjs.length}</span><span className="k">个平台</span></div>
            <div><span className="v">{event.heat}</span><span className="k">综合热度</span></div>
          </div>
        </header>
        <section className="drawer-section">
          <h4 className="drawer-label">扩散时间线</h4>
          <div className="drawer-timeline">
            {sortedTimeline.map((n, i) => {
              const p = pmap.get(n.platform_id)
              return (
                <div key={n.id} className="timeline-item">
                  <div className="timeline-time" title={n.source_updated_ts ? new Date(n.source_updated_ts).toLocaleString('zh-CN') : ''}>
                    {fmtHM(n.source_updated_ts, n.first_crawl_time)}
                  </div>
                  <div className="timeline-dot" style={{ background: p?.color }}/>
                  <div className="timeline-body">
                    <div className="timeline-plat">
                      <PlatformAvatar p={p} size={16}/>
                      <span>{p?.name}</span>
                      {i === 0 && <span className="first-tag">首发</span>}
                    </div>
                    <div className="timeline-title">{n.title_zh && n.title_zh !== n.title ? n.title_zh : n.title}</div>
                  </div>
                </div>
              )
            })}
          </div>
        </section>
        <section className="drawer-section">
          <h4 className="drawer-label">按平台分组</h4>
          {Object.entries(byPlat).map(([pid, list]) => {
            const p = pmap.get(pid)
            if (!p) return null
            return (
              <div key={pid} className="drawer-plat-group">
                <div className="drawer-plat-head">
                  <PlatformAvatar p={p} size={18}/>
                  <span style={{ fontWeight: 500 }}>{p.name}</span>
                  <span style={{ color: 'var(--fg-mute)', fontFamily: 'var(--font-mono)', fontSize: 11 }}>{p.category}</span>
                  <span style={{ marginLeft: 'auto', fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--fg-mute)' }}>{list.length} 条</span>
                </div>
                {list.map(n => (
                  <div key={n.id} className="drawer-news" onClick={() => n.url && window.open(n.url, '_blank', 'noopener,noreferrer')}>
                    <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--fg-mute)', minWidth: 20 }}>#{n.rank}</span>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontSize: 14, fontWeight: 500, lineHeight: 1.4 }}>{n.title_zh && n.title_zh !== n.title ? n.title_zh : n.title}</div>
                        {n.title_zh && n.title_zh !== n.title && <div style={{ fontSize: 12, color: 'var(--fg-dim)', fontStyle: 'italic', marginTop: 2 }}>{n.title}</div>}
                        {n.description && <div style={{ fontSize: 12, color: 'var(--fg-dim)', marginTop: 6, lineHeight: 1.5 }}>{n.description}</div>}
                        {n.url && (
                          <a href={n.url} target="_blank" rel="noopener noreferrer" className="origin-link"
                             onClick={e => e.stopPropagation()} style={{ display: 'inline-block', marginTop: 6 }}>原文 ↗</a>
                        )}
                      </div>
                      <button className="bookmark-btn" data-on={bookmarks.has(n.id)} onClick={e => { e.stopPropagation(); toggleBookmark(n.id) }}>
                        <Icon.bookmark filled={bookmarks.has(n.id)} style={{ width: 15, height: 15 }}/>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )
          })}
        </section>
      </aside>
    </>
  )
}

/* ================= MAIN APP ================= */
export default function App() {
  const { fetchAll } = useNewsStore()
  const [view, setView] = useState(() => {
    const v = localStorage.getItem('radar.view')
    if (!v || v === 'events') return 'home'
    return v
  })
  const [theme, setTheme] = useState(() => localStorage.getItem('radar.theme') || 'dark')
  const [density, setDensity] = useState(() => localStorage.getItem('radar.density') || 'normal')
  const [layout, setLayout] = useState(() => localStorage.getItem('radar.layout') || 'standard')
  const [showReason, setShowReason] = useState(true)
  const [heroStyle, setHeroStyle] = useState<'cards' | 'band'>('cards')
  const [platformFilter, setPlatformFilter] = useState<string | null>(null)
  const [interestFilter, setInterestFilter] = useState<number | null>(null)
  const [search, setSearch] = useState('')
  const [sortBy, setSortBy] = useState<'personal' | 'heat' | 'time'>('personal')
  const [activeTag, setActiveTag] = useState<string | null>(null)
  const [tweaksOpen, setTweaksOpen] = useState(false)
  const [isMobile, setIsMobile] = useState(() => window.innerWidth <= 760)
  const [openEvent, setOpenEvent] = useState<TimelineEvent | null>(null)
  const [lastRefresh, setLastRefresh] = useState<number>(0)
  const [streamOn, setStreamOn] = useState(false)

  useEffect(() => { fetchAll().then(() => setLastRefresh(Date.now())) }, [])
  useEffect(() => {
    const base = (import.meta as any).env?.DEV ? 'http://localhost:8001/api/timeline' : '/api/timeline'
    const es = new EventSource(`${base}/stream`)
    es.addEventListener('open', () => setStreamOn(true))
    es.addEventListener('update', () => {
      fetchAll().then(() => setLastRefresh(Date.now()))
    })
    es.addEventListener('error', () => setStreamOn(false))
    return () => { es.close() }
  }, [fetchAll])
  useEffect(() => {
    const onResize = () => setIsMobile(window.innerWidth <= 760)
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])
  useEffect(() => { document.documentElement.setAttribute('data-theme', theme); localStorage.setItem('radar.theme', theme) }, [theme])
  useEffect(() => { document.documentElement.setAttribute('data-density', density); localStorage.setItem('radar.density', density) }, [density])
  useEffect(() => { localStorage.setItem('radar.layout', layout) }, [layout])
  useEffect(() => { localStorage.setItem('radar.view', view) }, [view])

  const filters = { platformFilter, interestFilter, search, sortBy, activeTag }

  return (
    <div className="app" data-layout={layout} data-view={view}>
      <Topbar view={view} setView={setView} search={search} setSearch={setSearch} onTweaks={() => setTweaksOpen(v => !v)} isMobile={isMobile}/>

      {!isMobile && (
        <Sidebar
          platformFilter={platformFilter} setPlatformFilter={setPlatformFilter}
          interestFilter={interestFilter} setInterestFilter={setInterestFilter}
        />
      )}

      <main className="main">
        {layout === 'briefing' ? (
          <BriefingView/>
        ) : (
          <>
            {view === 'feed' && (
              <>
                <div className="toolbar sticky">
                  <div className="pill-filters">
                    <button className="pill" data-active={sortBy === 'personal'} onClick={() => setSortBy('personal')}>综合分</button>
                    <button className="pill" data-active={sortBy === 'heat'} onClick={() => setSortBy('heat')}>AI 热度</button>
                    <button className="pill" data-active={sortBy === 'time'} onClick={() => setSortBy('time')}>最新</button>
                    <span style={{ width: 1, background: 'var(--line)', margin: '0 4px' }}/>
                    {['科技', 'AI', '财经', '新能源', '社会', '学术'].map(t => (
                      <button key={t} className="pill" data-active={activeTag === t} onClick={() => setActiveTag(activeTag === t ? null : t)}>#{t}</button>
                    ))}
                  </div>
                </div>
                <FeedView filters={filters} showReason={showReason}/>
              </>
            )}
            {view === 'home' && <HomeView onOpenEvent={setOpenEvent}/>}
            {view === 'platforms' && <PlatformsView onGoToFeed={(pid) => { setPlatformFilter(pid); setView('feed') }}/>}
            {view === 'bookmarks' && <BookmarksView showReason={showReason}/>}
          </>
        )}
      </main>

      {!isMobile && <Rightbar
        activeTag={activeTag} setActiveTag={setActiveTag}
        interestFilter={interestFilter} setInterestFilter={setInterestFilter}
        platformFilter={platformFilter} setPlatformFilter={setPlatformFilter}
        setView={setView}
      />}

      {isMobile && (
        <nav className="mobile-nav">
          <button data-active={view === 'home'} onClick={() => setView('home')}><Icon.radar/>主页</button>
          <button data-active={view === 'feed'} onClick={() => setView('feed')}><Icon.feed/>FEED</button>
          <button data-active={view === 'platforms'} onClick={() => setView('platforms')}><Icon.grid/>平台</button>
          <button data-active={view === 'bookmarks'} onClick={() => setView('bookmarks')}><Icon.bookmark/>收藏</button>
        </nav>
      )}

      <EventDrawer event={openEvent} onClose={() => setOpenEvent(null)}/>

      <TweaksPanel
        open={tweaksOpen} onClose={() => setTweaksOpen(false)}
        theme={theme} setTheme={setTheme}
        density={density} setDensity={setDensity}
        showReason={showReason} setShowReason={setShowReason}
        heroStyle={heroStyle} setHeroStyle={setHeroStyle}
        layout={layout} setLayout={setLayout}
        lastRefresh={lastRefresh}
        streamOn={streamOn}
        onRefreshNow={() => fetchAll().then(() => setLastRefresh(Date.now()))}
      />
    </div>
  )
}
