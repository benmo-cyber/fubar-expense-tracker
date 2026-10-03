import { useEffect, useMemo, useState } from 'react'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

type Person = {
  id: string
  email: string
  full_name: string
  role: string
  is_active: boolean
  is_superuser: boolean
  supervisor_id: string | null
}

function childrenOf(people: Person[], supervisorId: string) {
  return people
    .filter((person) => person.supervisor_id === supervisorId && person.id !== supervisorId)
    .sort((a, b) => a.full_name.localeCompare(b.full_name))
}

function rootsOf(people: Person[]) {
  const ids = new Set(people.map((person) => person.id))
  return people
    .filter((person) => !person.supervisor_id || person.supervisor_id === person.id || !ids.has(person.supervisor_id))
    .sort((a, b) => Number(b.is_superuser) - Number(a.is_superuser) || a.full_name.localeCompare(b.full_name))
}

function reportsTo(people: Person[], personId: string, supervisorId: string) {
  let current: string | null = supervisorId
  const seen = new Set<string>()
  while (current) {
    if (current === personId || seen.has(current)) return true
    seen.add(current)
    current = people.find((person) => person.id === current)?.supervisor_id || null
  }
  return false
}

function OrgNode({ person, people, selectedId, onSelect, trail }: {
  person: Person
  people: Person[]
  selectedId: string
  onSelect: (id: string) => void
  trail: string[]
}) {
  if (trail.includes(person.id)) return null
  const reports = childrenOf(people, person.id)
  const selected = person.id === selectedId
  const nextTrail = [...trail, person.id]
  return (
    <li>
      <button
        type="button"
        onClick={() => onSelect(person.id)}
        className={`w-44 rounded-2xl bg-white px-3 py-3 text-left shadow-sm ${selected ? 'ring-2 ring-[#1D6FE8]' : ''} ${person.is_active ? '' : 'opacity-60'}`}
      >
        <p className="font-semibold text-[#0B3D73]">{person.full_name}</p>
        <p className="text-xs capitalize text-[#5B6B7C]">
          {person.role}{person.is_superuser ? ' · superuser' : ''}{person.is_active ? '' : ' · inactive'}
        </p>
      </button>
      {reports.length > 0 ? (
        <ul>
          {reports.map((report) => (
            <OrgNode key={report.id} person={report} people={people} selectedId={selectedId} onSelect={onSelect} trail={nextTrail} />
          ))}
        </ul>
      ) : null}
    </li>
  )
}

export default function People() {
  const [people, setPeople] = useState<Person[]>([])
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [role, setRole] = useState('sales')
  const [supervisorId, setSupervisorId] = useState('')
  const [issuedPassword, setIssuedPassword] = useState('')
  const [error, setError] = useState('')
  const [selectedId, setSelectedId] = useState('')
  const [rename, setRename] = useState('')
  const [showInvite, setShowInvite] = useState(false)

  async function load() {
    const { data } = await api.get<Person[]>('/people')
    setPeople(data)
    if (!supervisorId && data[0]) setSupervisorId(data.find((person) => person.is_superuser)?.id || data[0].id)
    setSelectedId((current) => current || data.find((person) => person.is_superuser)?.id || data[0]?.id || '')
  }

  useEffect(() => {
    void load()
  }, [])

  const selected = people.find((person) => person.id === selectedId) || null
  const roots = useMemo(() => rootsOf(people), [people])

  useEffect(() => {
    if (selected) setRename(selected.full_name)
  }, [selected?.id])

  async function invite(event: React.FormEvent) {
    event.preventDefault()
    setError('')
    setIssuedPassword('')
    try {
      const { data } = await api.post<Person & { temporary_password: string }>('/people', {
        email,
        full_name: fullName,
        role,
        supervisor_id: supervisorId || null,
      })
      setIssuedPassword(data.temporary_password)
      setFullName('')
      setEmail('')
      setSelectedId(data.id)
      await load()
    } catch {
      setError('That person could not be invited. Check the email is new.')
    }
  }

  async function save(person: Person, patch: Partial<Person>) {
    setError('')
    try {
      await api.patch(`/people/${person.id}`, patch)
      await load()
    } catch {
      setError('That change was not saved.')
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-3xl font-bold text-[#0B3D73]">People</h1>
          <p className="text-muted-foreground">The chart follows each person’s supervisor. Select someone to rename, move, or deactivate them.</p>
        </div>
        <Button variant="outline" onClick={() => setShowInvite(!showInvite)}>{showInvite ? 'Close invite' : 'Invite someone'}</Button>
      </div>

      {showInvite ? (
        <Card className="border-0 shadow-sm">
          <CardHeader>
            <CardTitle>Invite</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={invite} className="grid gap-3 md:grid-cols-2">
              <div>
                <Label>Name</Label>
                <Input className="mt-1" value={fullName} onChange={(event) => setFullName(event.target.value)} required />
              </div>
              <div>
                <Label>Email</Label>
                <Input className="mt-1" value={email} onChange={(event) => setEmail(event.target.value)} required />
              </div>
              <div>
                <Label>Role</Label>
                <select className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm" value={role} onChange={(event) => setRole(event.target.value)}>
                  <option value="sales">Salesperson</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
              <div>
                <Label>Supervisor</Label>
                <select className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm" value={supervisorId} onChange={(event) => setSupervisorId(event.target.value)}>
                  {people.filter((person) => person.is_active).map((person) => (
                    <option key={person.id} value={person.id}>{person.full_name}</option>
                  ))}
                </select>
              </div>
              <div className="md:col-span-2">
                <Button type="submit">Create account</Button>
              </div>
            </form>
            {issuedPassword ? <p className="mt-4 text-sm">Temporary password, shown once: <strong>{issuedPassword}</strong></p> : null}
          </CardContent>
        </Card>
      ) : null}

      <div className="overflow-x-auto rounded-2xl bg-[#EAF1F8] px-4 py-8">
        {roots.length > 0 ? (
          <ul className="org-tree">
            {roots.map((person) => (
              <OrgNode key={person.id} person={person} people={people} selectedId={selectedId} onSelect={setSelectedId} trail={[]} />
            ))}
          </ul>
        ) : (
          <p className="text-center text-muted-foreground">No people yet.</p>
        )}
      </div>

      {selected ? (
        <Card className="border-0 shadow-sm">
          <CardContent className="grid gap-4 pt-6 md:grid-cols-[1fr_auto]">
            <div>
              <p className="text-lg font-semibold text-[#0B3D73]">{selected.full_name}</p>
              <p className="text-sm text-muted-foreground">{selected.email}</p>
              <div className="mt-3 flex flex-wrap items-end gap-2">
                <div>
                  <Label>Name</Label>
                  <Input className="mt-1" value={rename} onChange={(event) => setRename(event.target.value)} />
                </div>
                <Button variant="outline" onClick={() => void save(selected, { full_name: rename.trim() })}>Save name</Button>
              </div>
            </div>
            <div className="flex flex-wrap content-start gap-2">
              <div>
                <Label>Reports to</Label>
                <select
                  className="mt-1 rounded-md border bg-background px-3 py-2 text-sm"
                  value={selected.supervisor_id || ''}
                  onChange={(event) => {
                    const next = event.target.value
                    if (!next) return
                    if (reportsTo(people, selected.id, next)) {
                      setError('That would put this person above their own supervisor.')
                      return
                    }
                    void save(selected, { supervisor_id: next })
                  }}
                >
                  {!selected.supervisor_id ? <option value="">Choose a supervisor</option> : null}
                  {people.filter((person) => person.id !== selected.id).map((person) => (
                    <option key={person.id} value={person.id}>{person.full_name}</option>
                  ))}
                </select>
              </div>
              <Button variant="outline" onClick={() => void save(selected, { role: selected.role === 'admin' ? 'sales' : 'admin' })}>
                Make {selected.role === 'admin' ? 'salesperson' : 'admin'}
              </Button>
              <Button variant="outline" onClick={() => void save(selected, { is_active: !selected.is_active })}>
                {selected.is_active ? 'Deactivate' : 'Reactivate'}
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : null}
      {error ? <p className="text-sm text-red-600">{error}</p> : null}
    </div>
  )
}
