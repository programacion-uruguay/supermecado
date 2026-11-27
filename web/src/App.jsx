import { useEffect, useMemo, useState } from 'react'

const SUPERMARKET_COLORS = {
  tienda_inglesa: '#0284c7',
  disco: '#dc2626',
  devoto: '#ea580c',
  geant: '#2563eb',
  tata: '#e11d48',
  frog: '#16a34a',
  el_dorado: '#ca8a04',
  el_clon: '#7c3aed',
  redmarket5: '#b91c1c',
  '5oceanos': '#0369a1',
  artico: '#0891b2',
  congelados_uy: '#2563eb',
  marmatu: '#0d9488',
  portisur: '#4f46e5',
  glacial: '#0284c7',
}

const QUICK_SEARCHES = ['Aceite', 'Yerba', 'Leche', 'Arroz', 'Fideos']

const CANASTA_BASICA_ITEMS = [
  { label: 'Yerba 1 kg', keywords: ['yerba', '1 kg'], fallback: ['yerba'] },
  { label: 'Leche entera 1 L', keywords: ['leche', 'entera'], fallback: ['leche'] },
  { label: 'Arroz blanco 1 kg', keywords: ['arroz', '1 kg'], fallback: ['arroz'] },
  { label: 'Aceite de girasol', keywords: ['aceite', 'girasol'], fallback: ['aceite'] },
  { label: 'Fideos 500 g', keywords: ['fideos', '500'], fallback: ['fideos'] },
  { label: 'Azúcar 1 kg', keywords: ['azucar', '1 kg'], fallback: ['azucar'] },
  { label: 'Harina 1 kg', keywords: ['harina', '1 kg'], fallback: ['harina'] },
  { label: 'Sal', keywords: ['sal'], fallback: ['sal'] },
  { label: 'Pulpa de tomate', keywords: ['pulpa', 'tomate'], fallback: ['tomate'] },
  { label: 'Café', keywords: ['cafe'], fallback: ['cafe'] },
  { label: 'Detergente', keywords: ['detergente'], fallback: ['detergente'] },
  { label: 'Papel higiénico', keywords: ['papel', 'higienico'], fallback: ['papel higienico'] },
]

function formatUYU(value) {
  return `$ ${Number(value).toLocaleString('es-UY', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  })}`
}

function ProductCard({ product, cartQty, onAdd, onChangeQty }) {
  // Índice 0 siempre es el más barato porque la API ordena offers por precio ASC
  const [offerIndex, setOfferIndex] = useState(0)

  useEffect(() => {
    setOfferIndex(0)
  }, [product.id])

  const offers = product.offers || []
  const currentOffer = offers[offerIndex] || offers[0]
  if (!currentOffer) return null

  const totalOffers = offers.length
  const isBest = offerIndex === 0
  const dotColor = SUPERMARKET_COLORS[currentOffer.supermarket_slug] || '#64748b'
  const image = currentOffer.image_url || offers.find((o) => o.image_url)?.image_url

  function prevSuper() {
    setOfferIndex((prev) => (prev - 1 + totalOffers) % totalOffers)
  }

  function nextSuper() {
    setOfferIndex((prev) => (prev + 1) % totalOffers)
  }

  return (
    <article className="product-card">
      <div className="card-image-box">
        {isBest && <span className="best-corner-badge">Mejor precio</span>}
        {product.savings > 0 && (
          <span className="savings-corner-badge">-{product.savings_pct}%</span>
        )}
        {image ? (
          <img src={image} alt={product.name} loading="lazy" />
        ) : (
          <span style={{ fontSize: '2.6rem' }}>🛒</span>
        )}
      </div>

      <div className="card-info">
        <div className="card-brand-row">
          <span className="card-brand">
            {product.brand || 'Sin marca'}
          </span>
          {product.unit_size && (
            <span className="card-size">{product.unit_size}</span>
          )}
        </div>
        <h2 className="card-title" title={product.name}>
          {product.name}
        </h2>
      </div>

      <div className={`price-switcher ${isBest ? 'is-best' : ''}`}>
        <div className="switcher-top">
          <button
            type="button"
            className="arrow-btn"
            onClick={prevSuper}
            disabled={totalOffers <= 1}
            aria-label="Supermercado anterior"
            title="Ver otro supermercado"
          >
            ‹
          </button>

          <div className="super-pill">
            <span className="super-dot" style={{ backgroundColor: dotColor }} />
            <span>{currentOffer.supermarket_name}</span>
            {totalOffers > 1 && (
              <span className="super-counter">
                ({offerIndex + 1}/{totalOffers})
              </span>
            )}
          </div>

          <button
            type="button"
            className="arrow-btn"
            onClick={nextSuper}
            disabled={totalOffers <= 1}
            aria-label="Siguiente supermercado"
            title="Ver otro supermercado"
          >
            ›
          </button>
        </div>

        <div className="price-row">
          <div className="price-main">
            <div className="price-figures">
              <span className="price-value">{formatUYU(currentOffer.price)}</span>
              {currentOffer.list_price && (
                <span className="list-price">{formatUYU(currentOffer.list_price)}</span>
              )}
            </div>
            {currentOffer.unit_price && (
              <span className="unit-price">
                {formatUYU(currentOffer.unit_price)} / {currentOffer.unit_label}
              </span>
            )}
          </div>

          <a
            className="go-store-btn"
            href={currentOffer.url}
            target="_blank"
            rel="noreferrer"
          >
            Ir ↗
          </a>
        </div>
      </div>

      {cartQty > 0 ? (
        <div className="qty-control">
          <button
            type="button"
            className="qty-btn"
            onClick={() => onChangeQty(product.id, cartQty - 1)}
            aria-label="Restar"
          >
            −
          </button>
          <span>En changuito: {cartQty}</span>
          <button
            type="button"
            className="qty-btn"
            onClick={() => onChangeQty(product.id, cartQty + 1)}
            aria-label="Sumar"
          >
            +
          </button>
        </div>
      ) : (
        <button
          type="button"
          className="add-cart-btn"
          onClick={() => onAdd(product)}
        >
          + Agregar al changuito
        </button>
      )}
    </article>
  )
}

export default function App() {
  const [products, setProducts] = useState([])
  const [categories, setCategories] = useState([])
  const [brands, setBrands] = useState([])
  const [query, setQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('')
  const [selectedBrand, setSelectedBrand] = useState('')
  const [sortBy, setSortBy] = useState('min_price')
  const [activeTab, setActiveTab] = useState('shop')
  const [recipes, setRecipes] = useState([])
  const [allCatalogProducts, setAllCatalogProducts] = useState([])
  const [recipeQuery, setRecipeQuery] = useState('')
  const [recipeCategory, setRecipeCategory] = useState('')
  const [loading, setLoading] = useState(true)
  const [scraping, setScraping] = useState(false)
  const [staticMode, setStaticMode] = useState(false)
  const [staticCatalog, setStaticCatalog] = useState(null)
  const [message, setMessage] = useState('')
  const [cartOpen, setCartOpen] = useState(false)
  const [cart, setCart] = useState(() => {
    try {
      const saved = localStorage.getItem('super_pepito_cart')
      return saved ? JSON.parse(saved) : []
    } catch {
      return []
    }
  })

  useEffect(() => {
    try {
      localStorage.setItem('super_pepito_cart', JSON.stringify(cart))
    } catch {
      // ignore storage errors
    }
  }, [cart])

  function addToCart(product) {
    setCart((prev) => {
      const existing = prev.find((item) => item.id === product.id)
      if (existing) {
        return prev.map((item) =>
          item.id === product.id ? { ...item, qty: item.qty + 1 } : item,
        )
      }
      return [...prev, { ...product, qty: 1 }]
    })
  }

  function updateCartQty(productId, newQty) {
    if (newQty <= 0) {
      setCart((prev) => prev.filter((item) => item.id !== productId))
    } else {
      setCart((prev) =>
        prev.map((item) => (item.id === productId ? { ...item, qty: newQty } : item)),
      )
    }
  }

  const cartCount = useMemo(
    () => cart.reduce((sum, item) => sum + item.qty, 0),
    [cart],
  )

  const cartSummary = useMemo(() => {
    if (cart.length === 0) return { splitTotal: 0, ranking: [], maxSingleTotal: 0 }

    let splitTotal = 0
    const superMap = {}

    for (const item of cart) {
      const offers = item.offers || []
      if (offers.length > 0) {
        splitTotal += offers[0].price * item.qty
      }
      for (const off of offers) {
        if (!superMap[off.supermarket_slug]) {
          superMap[off.supermarket_slug] = {
            slug: off.supermarket_slug,
            name: off.supermarket_name,
            total: 0,
            matchedItems: 0,
          }
        }
        superMap[off.supermarket_slug].total += off.price * item.qty
        superMap[off.supermarket_slug].matchedItems += 1
      }
    }

    const ranking = Object.values(superMap).sort(
      (a, b) => b.matchedItems - a.matchedItems || a.total - b.total,
    )
    const completeSupers = ranking.filter((r) => r.matchedItems === cart.length)
    const maxSingleTotal =
      completeSupers.length > 0
        ? Math.max(...completeSupers.map((r) => r.total))
        : ranking[0]?.total || 0

    return { splitTotal, ranking, maxSingleTotal }
  }, [cart])

  async function loadCategories() {
    try {
      const [catRes, brandRes] = await Promise.all([
        fetch('/api/categories'),
        fetch('/api/brands'),
      ])
      if (catRes.ok && brandRes.ok) {
        setCategories(await catRes.json())
        setBrands(await brandRes.json())
        return
      }
      throw new Error('API no disponible')
    } catch {
      try {
        const res = await fetch('./data/catalog.json')
        if (!res.ok) throw new Error('Sin catalog.json')
        const data = await res.json()
        setStaticMode(true)
        setStaticCatalog(data)
        setCategories(data.categories || [])
        setBrands(data.brands || [])
      } catch (err) {
        console.error('Error cargando filtros:', err)
      }
    }
  }

  async function loadProducts() {
    setLoading(true)
    if (staticMode && staticCatalog) {
      const qLower = query.trim().toLowerCase()
      const filtered = (staticCatalog.products || []).filter((p) => {
        if (qLower) {
          const inName = (p.name || '').toLowerCase().includes(qLower)
          const inBrand = (p.brand || '').toLowerCase().includes(qLower)
          if (!inName && !inBrand) return false
        }
        if (selectedCategory && p.category !== selectedCategory) return false
        if (selectedBrand && (p.brand || '').toLowerCase() !== selectedBrand.toLowerCase()) {
          return false
        }
        return true
      })
      setProducts(filtered)
      setMessage('')
      setLoading(false)
      return
    }

    try {
      const params = new URLSearchParams()
      if (query.trim()) params.set('q', query.trim())
      if (selectedCategory) params.set('category', selectedCategory)
      if (selectedBrand) params.set('brand', selectedBrand)

      const res = await fetch(`/api/products?${params.toString()}`)
      if (!res.ok) throw new Error('Error consultando productos')
      const data = await res.json()
      setProducts(data)
      setMessage('')
    } catch {
      try {
        const res = await fetch('./data/catalog.json')
        if (!res.ok) throw new Error('Sin catalog.json')
        const data = await res.json()
        setStaticMode(true)
        setStaticCatalog(data)
        setCategories(data.categories || [])
        setBrands(data.brands || [])
        setProducts(data.products || [])
        setMessage('')
      } catch {
        setMessage('No se pudo conectar con la API de Python ni con el catálogo estático.')
      }
    } finally {
      setLoading(false)
    }
  }

  async function handleScrapeNow() {
    if (staticMode) {
      setMessage('En la versión web pública los precios se actualizan cuando corrés el scraper y volvés a subir (firebase deploy).')
      return
    }
    setScraping(true)
    setMessage('Actualizando precios desde los supermercados de Montevideo...')
    try {
      const params = new URLSearchParams()
      if (query.trim()) params.set('q', query.trim())
      const res = await fetch(`/api/scrape?${params.toString()}`, { method: 'POST' })
      if (res.ok) {
        setTimeout(() => {
          loadProducts()
          loadCategories()
          setScraping(false)
        }, 3500)
      } else {
        setScraping(false)
      }
    } catch {
      setScraping(false)
      setMessage('Error al iniciar la actualización.')
    }
  }

  useEffect(() => {
    loadCategories()
    fetch('./data/recipes.json')
      .then((r) => (r.ok ? r.json() : []))
      .then((data) => setRecipes(Array.isArray(data) ? data : []))
      .catch(() => {})
    fetch('./data/catalog.json')
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data && Array.isArray(data.products)) {
          setAllCatalogProducts(data.products)
        }
      })
      .catch(() => {})
  }, [])

  useEffect(() => {
    const timer = setTimeout(() => {
      loadProducts()
    }, 220)
    return () => clearTimeout(timer)
  }, [query, selectedCategory, selectedBrand, staticMode])

  const sortedProducts = useMemo(() => {
    const copy = [...products]
    if (sortBy === 'min_price') {
      copy.sort((a, b) => a.min_price - b.min_price)
    } else if (sortBy === 'unit_price') {
      copy.sort(
        (a, b) =>
          (a.min_unit_price ?? Number.MAX_SAFE_INTEGER) -
          (b.min_unit_price ?? Number.MAX_SAFE_INTEGER),
      )
    } else if (sortBy === 'savings') {
      copy.sort((a, b) => b.savings - a.savings || a.min_price - b.min_price)
    } else {
      copy.sort((a, b) => a.name.localeCompare(b.name))
    }
    return copy
  }, [products, sortBy])

  const filteredRecipes = useMemo(() => {
    const q = recipeQuery.trim().toLowerCase()
    return recipes.filter((r) => {
      if (recipeCategory && r.category !== recipeCategory) return false
      if (q) {
        const inTitle = (r.title || '').toLowerCase().includes(q)
        const inDesc = (r.description || '').toLowerCase().includes(q)
        const inIng = (r.ingredients || []).some((i) => i.toLowerCase().includes(q))
        if (!inTitle && !inDesc && !inIng) return false
      }
      return true
    })
  }, [recipes, recipeQuery, recipeCategory])

  const recipeCategories = useMemo(
    () => Array.from(new Set(recipes.map((r) => r.category).filter(Boolean))),
    [recipes],
  )

  const basketData = useMemo(() => {
    const source = allCatalogProducts.length > 0 ? allCatalogProducts : products
    if (source.length === 0) return { items: [], minTotal: 0, ranking: [] }

    const picked = []
    const usedIds = new Set()

    for (const entry of CANASTA_BASICA_ITEMS) {
      const findBest = (kws) =>
        source
          .filter((p) => {
            if (usedIds.has(p.id)) return false
            const text = `${p.name || ''} ${p.unit_size || ''}`.toLowerCase()
            return kws.every((kw) => text.includes(kw))
          })
          .sort((a, b) => (b.offers?.length || 0) - (a.offers?.length || 0) || a.min_price - b.min_price)[0]

      const match = findBest(entry.keywords) || findBest(entry.fallback)
      if (match) {
        usedIds.add(match.id)
        picked.push({ ...match, basketLabel: entry.label })
      }
    }

    const minTotal = picked.reduce((sum, p) => sum + (p.min_price || 0), 0)
    const superMap = {}
    for (const prod of picked) {
      for (const off of prod.offers || []) {
        if (!superMap[off.supermarket_slug]) {
          superMap[off.supermarket_slug] = {
            slug: off.supermarket_slug,
            name: off.supermarket_name,
            total: 0,
            count: 0,
          }
        }
        superMap[off.supermarket_slug].total += off.price
        superMap[off.supermarket_slug].count += 1
      }
    }
    const ranking = Object.values(superMap).sort(
      (a, b) => b.count - a.count || a.total - b.total,
    )

    return { items: picked, minTotal, ranking }
  }, [allCatalogProducts, products])

  function loadBasketToCart() {
    for (const item of basketData.items) {
      addToCart(item)
    }
    setCartOpen(true)
  }

  function searchIngredientPrice(ingredient) {
    setQuery(ingredient)
    setSelectedCategory('')
    setSelectedBrand('')
    setActiveTab('shop')
  }

  return (
    <>
      <header className="topbar">
        <div className="topbar-inner">
          <div className="store-logo">
            <div className="store-icon">🛒</div>
            <div>
              <div className="store-name">Súper Pepito</div>
              <div className="store-sub">Montevideo · Siempre al mejor precio</div>
            </div>
          </div>

          <div className="nav-tabs">
            <button
              type="button"
              className={`nav-tab ${activeTab === 'shop' ? 'active' : ''}`}
              onClick={() => setActiveTab('shop')}
            >
              🏪 Góndola
            </button>
            <button
              type="button"
              className={`nav-tab ${activeTab === 'basket' ? 'active' : ''}`}
              onClick={() => setActiveTab('basket')}
            >
              🧺 Canasta Básica
            </button>
            <button
              type="button"
              className={`nav-tab ${activeTab === 'recipes' ? 'active' : ''}`}
              onClick={() => setActiveTab('recipes')}
            >
              🍳 Recetas ({recipes.length})
            </button>
          </div>

          <div className="search-box">
            <svg
              className="search-icon"
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.2"
            >
              <circle cx="11" cy="11" r="8" />
              <path d="m21 21-4.3-4.3" />
            </svg>
            <input
              className="search-input"
              type="text"
              placeholder={
                activeTab === 'recipes'
                  ? 'Buscar receta o ingrediente (ej. churros, tacos, atún)...'
                  : '¿Qué producto buscás hoy? (ej. aceite, yerba, leche, arroz)...'
              }
              value={activeTab === 'recipes' ? recipeQuery : query}
              onChange={(e) =>
                activeTab === 'recipes'
                  ? setRecipeQuery(e.target.value)
                  : setQuery(e.target.value)
              }
            />
          </div>

          {activeTab === 'shop' && (
            <button className="btn-refresh" onClick={handleScrapeNow} disabled={scraping}>
              <span>{scraping ? '⏳' : '🔄'}</span>
              {scraping ? 'Actualizando...' : 'Actualizar precios'}
            </button>
          )}

          <button type="button" className="btn-cart" onClick={() => setCartOpen(true)}>
            <span>🛒 Changuito</span>
            <span className="cart-count-pill">{cartCount}</span>
          </button>
        </div>
      </header>

      {activeTab === 'basket' ? (
        <main className="container">
          <section className="basket-hero">
            <div>
              <h1>🧺 Canasta Básica de Montevideo</h1>
              <p>
                Selección automática de {basketData.items.length} productos esenciales comparados entre todos los supermercados para que sepas cuánto cuesta hoy el surtido básico.
              </p>
            </div>
            <div className="basket-total-box">
              <span className="basket-total-label">Costo mínimo combinado</span>
              <span className="basket-total-value">{formatUYU(basketData.minTotal)}</span>
              <button
                type="button"
                className="basket-load-btn"
                onClick={loadBasketToCart}
                disabled={basketData.items.length === 0}
              >
                + Cargar toda la canasta al changuito
              </button>
            </div>
          </section>

          {basketData.ranking.length > 0 && (
            <>
              <h2 className="section-title" style={{ marginBottom: 12 }}>
                🏪 Comparativa comprando la canasta en un solo súper
              </h2>
              <div className="basket-ranking">
                {basketData.ranking.slice(0, 6).map((sup, idx) => (
                  <div
                    key={sup.slug}
                    className={`basket-rank-card ${idx === 0 ? 'winner' : ''}`}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <strong>{sup.name}</strong>
                      {idx === 0 && <span className="best-tag">Más barato</span>}
                    </div>
                    <div style={{ fontSize: '1.25rem', fontWeight: 800 }}>
                      {formatUYU(sup.total)}
                    </div>
                    <span style={{ fontSize: '0.78rem', opacity: 0.8 }}>
                      {sup.count}/{basketData.items.length} productos disponibles
                    </span>
                  </div>
                ))}
              </div>
            </>
          )}

          <div className="grid">
            {basketData.items.map((product) => {
              const inCart = cart.find((c) => c.id === product.id)
              return (
                <ProductCard
                  key={product.id}
                  product={product}
                  cartQty={inCart ? inCart.qty : 0}
                  onAdd={addToCart}
                  onChangeQty={updateCartQty}
                />
              )
            })}
          </div>
        </main>
      ) : activeTab === 'recipes' ? (
        <>
          <nav className="aisles-bar" aria-label="Categorías de recetas">
            <div className="aisles-inner">
              <button
                type="button"
                className={`aisle-pill ${recipeCategory === '' ? 'active' : ''}`}
                onClick={() => setRecipeCategory('')}
              >
                Todas las recetas
              </button>
              {recipeCategories.map((cat) => (
                <button
                  key={cat}
                  type="button"
                  className={`aisle-pill ${recipeCategory === cat ? 'active' : ''}`}
                  onClick={() => setRecipeCategory(cat)}
                >
                  {cat}
                </button>
              ))}
            </div>
          </nav>

          <main className="container">
            <div className="toolbar">
              <div className="toolbar-left">
                <h1 className="section-title">🍳 Recetas y Cocina</h1>
                <span className="results-badge">{filteredRecipes.length} recetas</span>
              </div>
            </div>

            <div className="grid">
              {filteredRecipes.map((rec) => (
                <article key={rec.id} className="recipe-card">
                  <div className="recipe-thumb">
                    {rec.thumbnail ? (
                      <img src={rec.thumbnail} alt={rec.title} loading="lazy" />
                    ) : (
                      <span>{rec.type === 'drive' ? '📚' : '📖'}</span>
                    )}
                  </div>

                  <div className="card-info">
                    <div className="card-brand-row">
                      <span className="card-brand">{rec.category}</span>
                      <span className="card-size">
                        {rec.type === 'image' ? 'Imagen' : rec.type === 'pdf' ? 'PDF' : 'Google Drive'}
                      </span>
                    </div>
                    <h2 className="card-title">{rec.title}</h2>
                    <p className="recipe-desc">{rec.description}</p>
                  </div>

                  {rec.ingredients && rec.ingredients.length > 0 && (
                    <div>
                      <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#64748b', marginBottom: 6 }}>
                        Ver precios de ingredientes:
                      </div>
                      <div className="ing-chips">
                        {rec.ingredients.map((ing) => (
                          <button
                            key={ing}
                            type="button"
                            className="ing-chip"
                            onClick={() => searchIngredientPrice(ing)}
                          >
                            🔍 {ing}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  <a
                    className="recipe-open-btn"
                    href={rec.url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {rec.type === 'drive' ? 'Abrir libro en Drive ↗' : 'Ver receta ↗'}
                  </a>
                </article>
              ))}
            </div>
          </main>
        </>
      ) : (
        <>

      <nav className="aisles-bar" aria-label="Góndolas">
        <div className="aisles-inner">
          <button
            type="button"
            className={`aisle-pill ${selectedCategory === '' ? 'active' : ''}`}
            onClick={() => setSelectedCategory('')}
          >
            Todos los productos
          </button>
          {categories.map((cat) => (
            <button
              key={cat}
              type="button"
              className={`aisle-pill ${selectedCategory === cat ? 'active' : ''}`}
              onClick={() => setSelectedCategory(cat)}
            >
              {cat}
            </button>
          ))}
        </div>
      </nav>

      <main className="container">
        <div className="quick-chips">
          <span className="quick-label">Góndolas rápidas:</span>
          {QUICK_SEARCHES.map((term) => (
            <button
              key={term}
              type="button"
              className={`chip ${query.toLowerCase() === term.toLowerCase() ? 'active' : ''}`}
              onClick={() =>
                setQuery(query.toLowerCase() === term.toLowerCase() ? '' : term)
              }
            >
              {term}
            </button>
          ))}
          {(query || selectedCategory || selectedBrand) && (
            <button
              type="button"
              className="chip"
              onClick={() => {
                setQuery('')
                setSelectedCategory('')
                setSelectedBrand('')
              }}
            >
              ✕ Ver todo
            </button>
          )}
        </div>

        {message && <div className="status-banner">{message}</div>}

        <div className="toolbar">
          <div className="toolbar-left">
            <h1 className="section-title">
              {query.trim()
                ? `Resultados para "${query.trim()}"`
                : selectedCategory || 'Catálogo de productos'}
            </h1>
            <span className="results-badge">{sortedProducts.length} productos</span>
          </div>

          <div className="toolbar-filters">
            <select
              className="sort-select"
              value={selectedBrand}
              onChange={(e) => setSelectedBrand(e.target.value)}
              aria-label="Filtrar por marca"
            >
              <option value="">Todas las marcas</option>
              {brands.map((b) => (
                <option key={b} value={b}>
                  {b}
                </option>
              ))}
            </select>

            <select
              className="sort-select"
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              aria-label="Ordenar productos"
            >
              <option value="min_price">Ordenar: Menor precio</option>
              <option value="unit_price">Ordenar: Menor precio por kg/L</option>
              <option value="savings">Ordenar: Mayor ahorro</option>
              <option value="name">Ordenar: Nombre A-Z</option>
            </select>
          </div>
        </div>

        {loading ? (
          <div className="empty">Cargando góndola...</div>
        ) : sortedProducts.length === 0 ? (
          <div className="empty">
            No encontramos productos con ese nombre. Probá buscar <strong>aceite</strong>,{' '}
            <strong>yerba</strong> o <strong>leche</strong>.
          </div>
        ) : (
          <div className="grid">
            {sortedProducts.map((product) => {
              const inCart = cart.find((c) => c.id === product.id)
              return (
                <ProductCard
                  key={product.id}
                  product={product}
                  cartQty={inCart ? inCart.qty : 0}
                  onAdd={addToCart}
                  onChangeQty={updateCartQty}
                />
              )
            })}
          </div>
        )}

        <footer className="footer">
          Súper Pepito · Comparador de precios en Montevideo (UYU). Usá las flechas ‹ › en cada producto para comparar otros supermercados.
        </footer>
      </main>
        </>
      )}

      {cartOpen && (
        <div className="drawer-backdrop" onClick={() => setCartOpen(false)}>
          <aside className="drawer" onClick={(e) => e.stopPropagation()}>
            <div className="drawer-header">
              <h2>🛒 Tu Changuito ({cartCount})</h2>
              <button
                type="button"
                className="drawer-close"
                onClick={() => setCartOpen(false)}
              >
                ✕
              </button>
            </div>

            <div className="drawer-body">
              {cart.length === 0 ? (
                <div className="empty">
                  Tu changuito está vacío. Agregá productos desde la góndola para comparar en qué supermercado te sale más barato el surtido.
                </div>
              ) : (
                <>
                  {cart.map((item) => (
                    <div key={item.id} className="cart-item">
                      <div className="cart-item-info">
                        <div className="cart-item-name" title={item.name}>
                          {item.name}
                        </div>
                        <div className="cart-item-meta">
                          Desde {formatUYU(item.min_price)} · {item.cheapest_supermarket}
                        </div>
                      </div>
                      <div className="cart-item-actions">
                        <button
                          type="button"
                          className="mini-btn"
                          onClick={() => updateCartQty(item.id, item.qty - 1)}
                        >
                          −
                        </button>
                        <strong>{item.qty}</strong>
                        <button
                          type="button"
                          className="mini-btn"
                          onClick={() => updateCartQty(item.id, item.qty + 1)}
                        >
                          +
                        </button>
                      </div>
                    </div>
                  ))}

                  <div className="split-box">
                    <strong>💡 Compra inteligente (eligiendo el más barato de cada uno):</strong>
                    <div style={{ fontSize: '1.25rem', fontWeight: 800, marginTop: 4 }}>
                      {formatUYU(cartSummary.splitTotal)}
                    </div>
                    {cartSummary.maxSingleTotal > cartSummary.splitTotal && (
                      <div style={{ marginTop: 2 }}>
                        Ahorrás{' '}
                        <strong>
                          {formatUYU(cartSummary.maxSingleTotal - cartSummary.splitTotal)}
                        </strong>{' '}
                        frente al súper más caro.
                      </div>
                    )}
                  </div>

                  <div className="compare-box">
                    <h3 className="compare-title">🏪 Comprando todo en un solo súper</h3>
                    {cartSummary.ranking.map((sup, idx) => (
                      <div
                        key={sup.slug}
                        className={`super-rank-row ${idx === 0 ? 'winner' : ''}`}
                      >
                        <div>
                          <span>{sup.name}</span>{' '}
                          <span style={{ fontSize: '0.74rem', opacity: 0.8 }}>
                            ({sup.matchedItems}/{cart.length} prod.)
                          </span>
                        </div>
                        <strong>{formatUYU(sup.total)}</strong>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>

            {cart.length > 0 && (
              <div className="drawer-footer">
                <button
                  type="button"
                  className="clear-cart-btn"
                  onClick={() => setCart([])}
                >
                  Vaciar changuito
                </button>
                <strong>Mejor total: {formatUYU(cartSummary.splitTotal)}</strong>
              </div>
            )}
          </aside>
        </div>
      )}
    </>
  )
}
