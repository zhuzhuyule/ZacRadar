import { useState, useEffect } from 'react'
import Sidebar from './components/Sidebar'
import Timeline from './components/Timeline'
import SearchBar from './components/SearchBar'
import { useNewsStore } from './store/newsStore'

function App() {
  const [filter, setFilter] = useState<'featured' | 'all' | 'bookmarks'>('featured')
  const [cardWidth, setCardWidth] = useState<number>(800)
  const [zoom, setZoom] = useState<number>(1)
  const { fetchNews } = useNewsStore()

  useEffect(() => {
    fetchNews()
    
    const handleCardWidthChange = (event: CustomEvent<number>) => {
      setCardWidth(event.detail)
    }
    
    const handleZoomChange = (event: CustomEvent<number>) => {
      setZoom(event.detail)
    }
    
    window.addEventListener('card-width-change' as any, handleCardWidthChange as any)
    window.addEventListener('zoom-change' as any, handleZoomChange as any)
    return () => {
      window.removeEventListener('card-width-change' as any, handleCardWidthChange as any)
      window.removeEventListener('zoom-change' as any, handleZoomChange as any)
    }
  }, [])

  return (
    <div className="min-h-screen bg-bg-primary" style={{ zoom }}>
      <header className="fixed top-0 left-0 right-0 h-14 border-b border-border-light bg-bg-secondary/90 backdrop-blur z-50">
        <div className="flex items-center h-full px-6">
          <div className="text-lg font-bold text-text-primary">
            AI <span className="text-accent">Timeline</span>
          </div>
          <div className="flex-1 mx-8">
            <SearchBar />
          </div>
          <div className="text-sm text-text-muted">
            {new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
          </div>
        </div>
      </header>

      <div className="flex pt-14">
        <Sidebar filter={filter} onFilterChange={setFilter} />
        <main className="flex-1 p-6">
          <Timeline filter={filter} width={cardWidth} />
        </main>
      </div>
    </div>
  )
}

export default App
