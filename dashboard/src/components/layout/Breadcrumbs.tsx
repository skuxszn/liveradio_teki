import { useLocation, Link } from 'react-router-dom'

export default function Breadcrumbs() {
  const location = useLocation()
  const parts = location.pathname.split('/').filter(Boolean)
  const crumbs = [{ name: 'Home', to: '/' }, ...parts.map((p, i) => ({
    name: p.charAt(0).toUpperCase() + p.slice(1),
    to: '/' + parts.slice(0, i + 1).join('/'),
  }))]
  return (
    <nav aria-label="Breadcrumb" className="text-sm text-gray-500">
      <ol className="flex items-center gap-2">
        {crumbs.map((c, i) => (
          <li key={c.to} className="flex items-center gap-2">
            <Link to={c.to} className="hover:text-gray-900">{c.name}</Link>
            {i < crumbs.length - 1 && <span>/</span>}
          </li>
        ))}
      </ol>
    </nav>
  )
}


