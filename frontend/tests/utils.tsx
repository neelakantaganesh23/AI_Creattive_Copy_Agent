import { ThemeProvider } from '@mui/material';
import { render, type RenderOptions, type RenderResult } from '@testing-library/react';
import type { ReactElement } from 'react';
import { MemoryRouter } from 'react-router-dom';

import { AuthProvider } from '@/contexts/AuthProvider';
import { theme } from '@/theme/theme';
import type {
  AgentExecution,
  GenerationDetail,
  GenerationOutput,
  GenerationStatusResponse,
  User,
} from '@/types/models';

interface Options extends Omit<RenderOptions, 'wrapper'> {
  route?: string;
  withAuth?: boolean;
}

export const renderWithProviders = (
  ui: ReactElement,
  { route = '/', withAuth = true, ...options }: Options = {},
): RenderResult => {
  const Wrapper = ({ children }: { children: React.ReactNode }): JSX.Element => (
    <ThemeProvider theme={theme}>
      <MemoryRouter initialEntries={[route]}>
        {withAuth ? <AuthProvider>{children}</AuthProvider> : children}
      </MemoryRouter>
    </ThemeProvider>
  );
  return render(ui, { wrapper: Wrapper, ...options });
};

export const mockUser: User = {
  id: 2,
  name: 'Marketing User',
  email: 'marketer@example.com',
  role: 'marketer',
  is_active: true,
  created_at: '2026-01-01T09:00:00Z',
};

export const mockOutput: GenerationOutput = {
  channel: 'email',
  language: 'English',
  email: {
    headline: 'Run Lighter. Go Farther. Feel Unstoppable.',
    sub_heading:
      'Introducing AeroFlex Running Shoes, engineered for responsive speed, built for lasting comfort, and designed for every run.',
    cta: 'SHOP AEROFLEX RUNNING SHOES',
  },
  mobile: {
    superline: 'JUST LAUNCHED',
    pre_heading: 'AeroFlex for Performance Seekers',
    headline: 'Run Lighter. Go Farther.',
    sub_heading: 'AeroFlex Running Shoes: responsive speed and lasting comfort.',
    cta: 'SHOP AEROFLEX RUNNING SHOES',
  },
  sms: { description: 'AeroFlex Running Shoes has landed. Responsive speed. Shop now.' },
  quality: {
    status: 'passed',
    warnings: [],
    repetition_score: 0,
    repetition_fixed: false,
    violations: [],
    judge_score: 1,
    naturalness: 1,
    revisions: 0,
  },
  grounded: false,
  provider: 'mock',
  models: { fast: 'mock-fast', quality: 'mock-quality' },
};

export const buildSteps = (status: AgentExecution['status'] = 'completed'): AgentExecution[] =>
  [
    ['data_extraction', 'Data Extraction'],
    ['web_search_grounding', 'Web Search Grounding'],
    ['copy_generation', 'Copy Generation'],
    ['repetition_fix', 'Repetition Fix'],
    ['cta_optimization', 'CTA Optimization'],
    ['output_parsing', 'Output Parsing & Logging'],
  ].map(([agentName, title], index) => ({
    id: index + 1,
    generation_id: 1,
    agent_name: agentName as string,
    title: title as string,
    description: 'Stage description',
    sequence: index + 1,
    status,
    input_summary: null,
    output_json: null,
    error_message: null,
    model_name: 'mock-fast',
    duration_ms: 12,
    started_at: '2026-01-01T10:00:00Z',
    completed_at: '2026-01-01T10:00:01Z',
  }));

export const mockGeneration: GenerationDetail = {
  id: 1,
  user_id: 2,
  title: 'AeroFlex Running Shoes launch',
  brief: 'We are launching the new AeroFlex Running Shoes.',
  channel: 'email',
  language: 'English',
  status: 'completed',
  grounded: false,
  execution_time_ms: 1840,
  brand_id: 1,
  brand_name: 'AeroFlex',
  product_id: 1,
  product_name: 'AeroFlex Running Shoes',
  audience_segment_id: 3,
  audience_segment_name: 'Performance Seekers',
  output: mockOutput,
  provider: 'mock',
  error_code: null,
  error_message: null,
  agent_executions: buildSteps(),
  grounding_sources: [],
  created_at: '2026-01-01T10:00:00Z',
  updated_at: '2026-01-01T10:00:02Z',
};

export const mockStatus = (
  overrides: Partial<GenerationStatusResponse> = {},
): GenerationStatusResponse => ({
  id: 1,
  status: 'completed',
  progress: 1,
  execution_time_ms: 1840,
  error_code: null,
  error_message: null,
  steps: buildSteps(),
  output: mockOutput,
  ...overrides,
});
