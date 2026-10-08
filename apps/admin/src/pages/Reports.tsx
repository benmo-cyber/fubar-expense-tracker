import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Fold } from '@/components/Fold'
import { Input } from '@/components/ui/input'
import { formatCurrency, formatDate } from '@/lib/utils'

type Split = { name: string; amount: number }
type Trip = { id: string; name: string; total: number; by_gl: Split[]; by_merchant: Split[] }
type Line = {
  id: string
  merchant_name: string
  amount: number
  expense_date: string
  trip_name: string | null
  category_name: string | null
  gl_name: string | null
  gl_code: string | null
  parent_code?: string | null
  parent_name?: string | null
  receipt_url: string | null
  notes: string | null
}
type Report = {
  id: string
  user_name: string
  title: string
  period_start: string
  period_end: string
  status: string
  total: number
  review_notes: string | null
  trips: Trip[]
  by_gl: Split[]
  gl_groups?: { id?: string; code: string; name: string; amount: number; children: { code: string; name: string; amount: number; percent: number }[] }[]
  by_merchant: Split[]
  expenses: Line[]
}

function moneyTip({ active, payload, label }: { active?: boolean; payload?: { value: number }[]; label?: string }) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-lg border bg-white px-3 py-2 text-sm shadow-sm">
      <p className="font-medium text-[#0B3D73]">{label}</p>
      <p>{formatCurrency(payload[0].value)}</p>
    </div>
  )
}

const REPORT_STATUSES = ['submitted', 'draft', 'rejected', 'approved', 'finalized']

export default function Reports() {
  const [reports, setReports] = useState<Report[]>([])
  const [error, setError] = useState('')
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState('all')
  const navigate = useNavigate()

  useEffect(() => {
    api.get<Report[]>('/reports')
      .then(({ data }) => setReports(data))
      .catch(() => setError('Reports could not be loaded.'))
  }, [])

  const needle = query.trim().toLowerCase()
  const visible = reports.filter((report) => {
    const matchesStatus = status === 'all' || report.status === status
    const matchesQuery = !needle || `${report.user_name} ${report.title}`.toLowerCase().includes(needle)
    return matchesStatus && matchesQuery
  })
  const people = Array.from(new Set(visible.map((report) => report.user_name))).sort()

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-black tracking-[0.22em] text-[#1D6FE8]">FUBAR</p>
        <h1 className="text-3xl font-bold text-[#0B3D73]">Reports</h1>
        <p className="text-muted-foreground">Grouped by person. Open a group, then a report, for the lines and receipt photos.</p>
      </div>
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => setStatus('all')}
          className={`rounded-full px-3 py-1.5 text-sm font-semibold ${status === 'all' ? 'bg-[#0B3D73] text-white' : 'bg-white text-[#0B3D73]'}`}
        >
          All {reports.length}
        </button>
        {REPORT_STATUSES.filter((item) => reports.some((report) => report.status === item)).map((item) => (
          <button
            key={item}
            type="button"
            onClick={() => setStatus(item)}
            className={`rounded-full px-3 py-1.5 text-sm font-semibold capitalize ${status === item ? 'bg-[#0B3D73] text-white' : 'bg-white text-[#0B3D73]'}`}
          >
            {item} {reports.filter((report) => report.status === item).length}
          </button>
        ))}
      </div>
      <Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search a person or report" />
      {error ? <p className="text-sm text-red-600">{error}</p> : null}
      <div className="space-y-3">
        {people.map((name) => {
          const rows = visible.filter((report) => report.user_name === name)
          const total = rows.reduce((sum, report) => sum + report.total, 0)
          return (
            <Fold key={name} title={name} meta={`${rows.length} ${rows.length === 1 ? "report" : "reports"} · ${formatCurrency(total)}`} forceOpen={needle.length > 0}>
              <table className="w-full text-left text-sm">
                <tbody>
                  {rows.map((report) => (
                    <tr
                      key={report.id}
                      className="cursor-pointer border-b last:border-0 hover:bg-blue-50"
                      onClick={() => navigate(`/reports/${report.id}`)}
                    >
                      <td className="px-4 py-3">
                        <span className="font-medium text-[#0B3D73]">{report.title}</span>
                        <span className="mt-0.5 block text-xs text-muted-foreground">
                          {formatDate(report.period_start)} – {formatDate(report.period_end)}
                        </span>
                      </td>
                      <td className="px-4 py-3 capitalize">{report.status}</td>
                      <td className="px-4 py-3 text-right font-semibold">{formatCurrency(report.total)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Fold>
          )
        })}
        {people.length === 0 && !error ? <p className="text-muted-foreground">No reports match.</p> : null}
      </div>
    </div>
  )
}

export function ReportDetail() {
  const { reportId } = useParams()
  const navigate = useNavigate()
  const [report, setReport] = useState<Report | null>(null)
  const [notes, setNotes] = useState('')
  const [error, setError] = useState('')
  const [photo, setPhoto] = useState<string | null>(null)

  async function load() {
    const { data } = await api.get<Report>(`/reports/${reportId}`)
    setReport(data)
  }

  useEffect(() => {
    load().catch(() => setError('That report could not be opened.'))
  }, [reportId])

  async function download(fileFormat: 'xlsx' | 'csv') {
    const response = await api.get(`/reports/${reportId}/export`, {
      params: { file_format: fileFormat },
      responseType: 'blob',
    })
    const url = URL.createObjectURL(response.data)
    const link = document.createElement('a')
    link.href = url
    link.download = `FUBAR-${report?.user_name || 'report'}-${report?.title || 'expenses'}.${fileFormat}`
    link.click()
    URL.revokeObjectURL(url)
  }

  async function act(path: string, body?: object) {
    setError('')
    try {
      await api.post(`/reports/${reportId}/${path}`, body)
      await load()
    } catch {
      setError('That report could not be updated.')
    }
  }

  if (!report) {
    return <p className="text-muted-foreground">{error || 'Opening report…'}</p>
  }

  return (
    <div className="space-y-6">
      <button type="button" className="text-sm font-semibold text-[#1D6FE8]" onClick={() => navigate('/reports')}>
        All reports
      </button>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-sm font-black tracking-[0.22em] text-[#1D6FE8]">FUBAR</p>
          <h1 className="text-3xl font-bold text-[#0B3D73]">{report.user_name}</h1>
          <p className="text-muted-foreground">
            {report.title} · {formatDate(report.period_start)} – {formatDate(report.period_end)} · {report.status} · {formatCurrency(report.total)}
          </p>
        </div>
        <div className="flex gap-2">
          <Button className="bg-[#1D6FE8] hover:bg-[#0B4F8A]" onClick={() => void download('xlsx')}>Excel</Button>
          <Button variant="outline" onClick={() => void download('csv')}>CSV</Button>
        </div>
      </div>
      {report.review_notes ? <p className="rounded-xl bg-white p-4 text-sm shadow-sm">Notes: {report.review_notes}</p> : null}
      {error ? <p className="text-sm text-red-600">{error}</p> : null}

      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="border-0 shadow-sm">
          <CardHeader><CardTitle className="text-[#0B3D73]">By GL account</CardTitle></CardHeader>
          <CardContent>
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={report.by_gl}>
                  <CartesianGrid vertical={false} stroke="#E6EEF8" />
                  <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#5B6B7C' }} interval={0} angle={-20} height={50} />
                  <YAxis hide />
                  <Tooltip content={<moneyTip />} />
                  <Bar dataKey="amount" fill="#0B4F8A" radius={[8, 8, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            {(report.gl_groups || []).filter((group) => group.children.length > 0).map((group) => (
              <div key={group.id || group.code} className="mt-4">
                <div className="flex items-center justify-between text-sm font-medium text-[#0B3D73]">
                  <span>{group.code} {group.name}</span>
                  <span>{formatCurrency(group.amount)}</span>
                </div>
                {group.children.map((child) => (
                  <div key={`${group.code}-${child.code}`} className="mt-1 flex items-center justify-between pl-4 text-sm text-[#334155]">
                    <span>{child.code} {child.name}</span>
                    <span>{formatCurrency(child.amount)} · {child.percent.toFixed(1)}%</span>
                  </div>
                ))}
              </div>
            ))}
          </CardContent>
        </Card>
        <Card className="border-0 shadow-sm">
          <CardHeader><CardTitle className="text-[#0B3D73]">By merchant</CardTitle></CardHeader>
          <CardContent className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={report.by_merchant}>
                <CartesianGrid vertical={false} stroke="#E6EEF8" />
                <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#5B6B7C' }} interval={0} angle={-20} height={50} />
                <YAxis hide />
                <Tooltip content={<moneyTip />} />
                <Bar dataKey="amount" fill="#1D6FE8" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      <Card className="border-0 shadow-sm">
        <CardHeader><CardTitle className="text-[#0B3D73]">Entries</CardTitle></CardHeader>
        <CardContent className="overflow-x-auto p-0">
          <table className="w-full text-left text-sm">
            <thead className="border-b text-[#5B6B7C]">
              <tr>
                <th className="px-4 py-3 font-medium">Date</th>
                <th className="px-4 py-3 font-medium">Merchant</th>
                <th className="px-4 py-3 font-medium">Account</th>
                <th className="px-4 py-3 font-medium">GL</th>
                <th className="px-4 py-3 font-medium">Trip</th>
                <th className="px-4 py-3 text-right font-medium">Amount</th>
              </tr>
            </thead>
            <tbody>
              {report.expenses.map((line) => (
                <tr key={line.id} className="border-b last:border-0">
                  <td className="px-4 py-3">{formatDate(line.expense_date)}</td>
                  <td className="px-4 py-3">{line.merchant_name}</td>
                  <td className="px-4 py-3">{line.category_name}</td>
                  <td className="px-4 py-3">
                    {line.gl_code} {line.gl_name}
                    {line.parent_code ? <div className="text-xs text-[#5B6B7C]">Under {line.parent_code} {line.parent_name}</div> : null}
                  </td>
                  <td className="px-4 py-3">{line.trip_name || '—'}</td>
                  <td className="px-4 py-3 text-right font-semibold">{formatCurrency(line.amount)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>

      <div>
        <h2 className="mb-3 text-lg font-semibold text-[#0B3D73]">Receipts</h2>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {report.expenses.map((line) => (
            <button
              key={line.id}
              type="button"
              className="overflow-hidden rounded-xl bg-white text-left shadow-sm"
              onClick={() => line.receipt_url && setPhoto(line.receipt_url)}
            >
              {line.receipt_url ? (
                <img src={line.receipt_url} alt={`${line.merchant_name} receipt`} className="h-40 w-full object-cover" />
              ) : (
                <div className="flex h-40 items-center justify-center bg-blue-50 text-sm text-[#0B3D73]">No photo</div>
              )}
              <p className="px-3 py-2 text-sm font-medium">{line.merchant_name}</p>
            </button>
          ))}
        </div>
      </div>

      {photo ? (
        <button type="button" className="fixed inset-0 z-20 flex items-center justify-center bg-[#0B3D73]/70 p-6" onClick={() => setPhoto(null)}>
          <img src={photo} alt="Receipt" className="max-h-[80vh] rounded-xl bg-white" />
        </button>
      ) : null}

      {report.status === 'submitted' ? (
        <div className="flex flex-wrap items-center gap-2">
          <Button className="bg-[#1D6FE8] hover:bg-[#0B4F8A]" onClick={() => void act('approve')}>Approve</Button>
          <Input className="max-w-sm" placeholder="What needs to change" value={notes} onChange={(event) => setNotes(event.target.value)} />
          <Button variant="outline" onClick={() => void act('reject', { notes })}>Send back</Button>
        </div>
      ) : null}
    </div>
  )
}
