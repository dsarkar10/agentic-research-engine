import { useState, type FormEvent } from "react"

interface SearchBarProps {
  onSearch: (query: string, deepSearch: boolean) => void
  disabled: boolean
}

export default function SearchBar({ onSearch, disabled }: SearchBarProps) {
  const [query, setQuery] = useState("")
  const [deepSearch, setDeepSearch] = useState(false)

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (!query.trim() || disabled) return
    onSearch(query.trim(), deepSearch)
  }

  return (
    <form onSubmit={handleSubmit} className="search-form">
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="e.g. How to use LangGraph for multi-agent systems..."
        disabled={disabled}
      />
      <button type="submit" disabled={disabled || !query.trim()}>
        {disabled ? "Researching..." : "Research"}
      </button>
    </form>
  )
}
