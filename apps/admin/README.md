# Expense Tracker Admin Portal

Modern React admin portal for expense approval and management.

## Features

- Dashboard with real-time statistics
- Expense review and approval workflow
- Bulk approve/reject functionality
- GL account mapping interface
- Export to CSV/JSON
- Responsive design with Tailwind CSS
- Modern UI with Shadcn/ui components

## Setup

### Install Dependencies

```bash
npm install
```

### Configure Environment

Create `.env.local`:

```env
VITE_API_URL=http://localhost:8000/api/v1
```

### Run Development Server

```bash
npm run dev
```

Visit http://localhost:5173

## Build for Production

```bash
npm run build
npm run preview
```

## Project Structure

```
admin/
├── src/
│   ├── components/
│   │   └── ui/           # Shadcn/ui components
│   ├── pages/
│   │   ├── Dashboard.tsx # Overview statistics
│   │   ├── Expenses.tsx  # Approval workflow
│   │   └── GLAccounts.tsx # GL mapping
│   ├── hooks/
│   │   ├── use-expenses.ts
│   │   └── use-gl-accounts.ts
│   ├── lib/
│   │   ├── api.ts        # Axios instance
│   │   └── utils.ts      # Helper functions
│   ├── types/            # TypeScript types
│   ├── App.tsx
│   └── main.tsx
├── package.json
├── vite.config.ts
└── tailwind.config.js
```

## Tech Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool
- **Tailwind CSS** - Styling
- **Shadcn/ui** - UI components
- **TanStack Query** - Data fetching
- **React Router** - Navigation
- **Axios** - HTTP client

## Features

### Dashboard
- Pending expense count and total
- Approved expense statistics
- Rejected expense count
- Recent expense list

### Expense Management
- List all pending expenses
- Individual approve/reject actions
- Bulk approval functionality
- Rejection with reason
- Filter by status and category

### GL Account Mapping
- View all category mappings
- Create new mappings
- Update existing mappings
- Delete mappings

## API Integration

All API calls use React Query for:
- Automatic caching
- Background refetching
- Optimistic updates
- Error handling

Example:

```typescript
const { data: expenses } = usePendingExpenses()
const approve = useApproveExpenses()

await approve.mutateAsync(['expense-id-1', 'expense-id-2'])
```

## Authentication

JWT tokens stored in localStorage:

```typescript
// Set token after login
localStorage.setItem('access_token', token)

// Token automatically added to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})
```

## Styling

Uses Tailwind CSS with custom design tokens:

```typescript
// Custom colors in tailwind.config.js
colors: {
  primary: "hsl(var(--primary))",
  destructive: "hsl(var(--destructive))",
  // ... more
}
```

## Components

### Shadcn/ui Components Used
- Button
- Card
- Input
- Label
- Table
- Select
- Dialog
- Dropdown Menu
- Toast

Add more with:

```bash
npx shadcn-ui@latest add [component-name]
```

## Testing

```bash
# Run tests
npm run test

# Coverage
npm run test:coverage
```

## Deployment

### Vercel

```bash
npm run build
vercel --prod
```

### Netlify

```bash
npm run build
netlify deploy --prod --dir=dist
```

### Docker

```dockerfile
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
```

### Static Hosting

Build and upload `dist/` folder to:
- AWS S3 + CloudFront
- Azure Blob Storage
- Google Cloud Storage

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| VITE_API_URL | Backend API base URL | http://localhost:8000/api/v1 |

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## Performance

- Code splitting with React lazy loading
- Image optimization
- Tree shaking in production
- Gzip compression
- CDN for static assets

## Accessibility

- Semantic HTML
- ARIA labels
- Keyboard navigation
- Screen reader support
- Focus management

## License

MIT
