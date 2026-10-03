import { useEffect, useState } from 'react'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Fold } from '@/components/Fold'
import { formatCurrency } from '@/lib/utils'

type Merchant = { id: string | null; name: string; amount: number; count: number }

export default function Merchants() {
  const [merchants, setMerchants] = useState<Merchant[]>([])
  const [intoId, setIntoId] = useState('')
  const [error, setError] = useState('')
  const [query, setQuery] = useState('')

  async function load() {
    const { data } = await api.get<Merchant[]>('/merchants')
    setMerchants(data)
    const first = data.find((merchant) => merchant.id)
    if (first?.id) setIntoId((current) => current || first.id || '')
  }

  useEffect(() => {
    void load()
  }, [])

  async function merge(id: string) {
    setError('')
    try {
      await api.post(`/merchants/${id}/merge?into_id=${intoId}`)
      await load()
    } catch {
      setError('Those merchants could not be merged.')
    }
  }

  const needle = query.trim().toLowerCase()
  const visible = merchants.filter((merchant) => merchant.name.toLowerCase().includes(needle))
  const letters = Array.from(new Set(visible.map((merchant) => (merchant.name[0] || '#').toUpperCase()))).sort()
  const kept = merchants.find((merchant) => merchant.id === intoId)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-[#0B3D73]">Merchants</h1>
        <p className="text-muted-foreground">
          {merchants.length} merchants · {formatCurrency(merchants.reduce((sum, merchant) => sum + merchant.amount, 0))}
          . Names that clearly match already share one profile. Open a letter to merge the rest.
        </p>
      </div>
      <div className="grid gap-3 md:grid-cols-[1fr_16rem]">
        <Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search merchants" />
        <select className="rounded-md border bg-background px-3 py-2 text-sm" value={intoId} onChange={(event) => setIntoId(event.target.value)}>
          {merchants.filter((merchant) => merchant.id).map((merchant) => (
            <option key={merchant.id} value={merchant.id || ''}>Keep {merchant.name}</option>
          ))}
        </select>
      </div>
      {error ? <p className="text-sm text-red-600">{error}</p> : null}
      <div className="space-y-3">
        {letters.map((letter) => {
          const rows = visible.filter((merchant) => (merchant.name[0] || '#').toUpperCase() === letter)
          const total = rows.reduce((sum, merchant) => sum + merchant.amount, 0)
          return (
            <Fold key={letter} title={letter} meta={`${rows.length} · ${formatCurrency(total)}`} forceOpen={needle.length > 0}>
              <ul>
                {rows.map((merchant) => (
                  <li key={merchant.id || merchant.name} className="flex items-center justify-between gap-3 border-b px-4 py-3 last:border-0">
                    <div>
                      <p className="font-medium text-[#0B3D73]">{merchant.name}</p>
                      <p className="text-sm text-muted-foreground">{merchant.count} expenses · {formatCurrency(merchant.amount)}</p>
                    </div>
                    {merchant.id && merchant.id !== intoId ? (
                      <Button variant="outline" onClick={() => void merge(merchant.id as string)}>
                        Merge into {kept?.name || 'kept merchant'}
                      </Button>
                    ) : (
                      <span className="text-xs font-semibold uppercase tracking-wide text-[#1D6FE8]">Kept</span>
                    )}
                  </li>
                ))}
              </ul>
            </Fold>
          )
        })}
        {letters.length === 0 ? <p className="text-muted-foreground">No merchants match.</p> : null}
      </div>
    </div>
  )
}
