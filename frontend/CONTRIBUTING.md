# Contributing to Floodingnaque Frontend

Thank you for contributing! This guide covers the development workflow, coding standards, and conventions used in this project.

## Development Workflow

1. **Create a feature branch** from `main`:
   ```bash
   git checkout -b feat/my-feature main
   ```
2. **Make changes** — follow the guidelines below.
3. **Write or update tests** for any new or changed behaviour.
4. **Verify locally:**
   ```bash
   npm run lint
   npm run test
   npm run build
   ```
5. **Create a pull request** with a clear description.
6. **Get review and approval** from at least one team member.
7. **Merge to `main`** — Vercel auto-deploys to production.

## Commit Messages

Format: `type: short description`

| Type       | When to use                    |
| ---------- | ------------------------------ |
| `feat`     | New feature                    |
| `fix`      | Bug fix                        |
| `docs`     | Documentation only             |
| `style`    | Formatting, whitespace         |
| `refactor` | Code restructuring (no behaviour change) |
| `test`     | Adding or updating tests       |
| `chore`    | Build, CI, dependency updates  |

Examples:

```
feat: add flood risk heatmap overlay
fix: prevent double-submit on prediction form
docs: update API endpoint table
```

## Code Style

- **TypeScript strict mode** — no `any` without justification.
- **Named exports** for components (not `export default`).
- **Functional components** with hooks — no class components (except `ErrorBoundary`).
- **Props interface** defined above the component.
- **Destructure props** in the function signature.
- Use `cn()` from `@/lib/utils` for conditional Tailwind classes.
- Colocate tests with source files: `MyComponent.test.tsx` next to `MyComponent.tsx`.

## Component Guidelines

Every component should handle **loading**, **error**, and **empty** states where applicable.

```tsx
interface MyComponentProps {
  title: string;
  isLoading?: boolean;
}

export function MyComponent({ title, isLoading = false }: MyComponentProps) {
  if (isLoading) return <Skeleton className="h-8 w-40" />;

  return <div className="text-lg font-semibold">{title}</div>;
}
```

### File Organisation (Feature Modules)

Each feature lives in `src/features/<name>/` with:

```
features/my-feature/
├── components/      # React components
├── hooks/           # Custom hooks (data fetching, logic)
├── services/        # API functions (e.g., myFeatureApi.ts)
├── utils/           # Pure helper functions (if needed)
└── index.ts         # Barrel exports
```

Export only the public surface from `index.ts`. Consumers import from `@/features/my-feature`, never from internal paths.

## Testing Guidelines

| Principle | Details |
| --------- | ------- |
| **Test user behaviour** | Use Testing Library queries (`getByRole`, `getByText`) — avoid implementation details. |
| **Mock APIs with MSW** | Handlers live in `src/tests/mocks/handlers.ts`. |
| **Use the custom render** | `src/test/utils.tsx` wraps components in providers. |
| **Aim for ≥ 70 % coverage** | Focus on critical paths (auth, predictions, alerts). |
| **Integration tests** | Complex flows belong in `src/tests/integration/`. |
| **E2E tests** | Playwright specs go in `e2e/`. Run with `npm run e2e`. |

### Running Tests

```bash
npm run test              # Vitest (all unit + integration)
npm run test:watch        # Watch mode
npm run test:coverage     # Coverage report
npm run e2e               # Playwright headless
npm run e2e:headed        # Playwright with browser UI
```

## State Management

| Kind | Library | Location | When to use |
| ---- | ------- | -------- | ----------- |
| **Server state** | TanStack Query | Feature `hooks/` | API data, caching, background refetch |
| **Client state** | Zustand | `src/state/stores/` | Auth, UI preferences, live SSE alerts |
| **Local state** | `useState` / `useReducer` | Component | Form inputs, toggles, ephemeral UI |

Do **not** put API data into Zustand. Use React Query for anything fetched from the backend.

## Adding a New Feature

1. Create `src/features/<name>/` with `components/`, `hooks/`, `services/`, `index.ts`.
2. Add API endpoints to `src/config/api.config.ts`.
3. Add TypeScript types to `src/types/api/`.
4. Create the page component in `src/app/<name>/page.tsx`.
5. Add the route in `src/App.tsx`.
6. Write tests alongside your components and hooks.
7. Export from `src/features/<name>/index.ts`.

## Questions?

Open an issue on GitHub or contact the team.
