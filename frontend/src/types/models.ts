/** Domain types mirroring the backend Pydantic schemas. */

export type Role = 'admin' | 'marketer' | 'viewer';
export type Channel = 'email' | 'mobile' | 'sms';
export type GenerationStatus = 'pending' | 'running' | 'completed' | 'partial' | 'failed';
export type AgentStatus = 'pending' | 'in_progress' | 'completed' | 'failed' | 'skipped';
export type QualityStatus = 'passed' | 'warning' | 'failed';

export type AuthProvider = 'local' | 'google';

export interface User {
  id: number;
  name: string;
  email: string;
  role: Role;
  is_active: boolean;
  created_at: string;
  auth_provider?: AuthProvider;
}

/** Which sign-in methods the server offers; read before rendering the login form. */
export interface AuthOptions {
  google_login_enabled: boolean;
  google_client_id: string | null;
  registration_enabled: boolean;
  password_reset_enabled: boolean;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
  refresh_token?: string | null;
}

export interface EmailCopy {
  headline: string;
  sub_heading: string;
  cta: string;
}

export interface MobileCopy {
  superline: string;
  pre_heading: string;
  headline: string;
  sub_heading: string;
  cta: string;
}

export interface SmsCopy {
  description: string;
}

export interface QualityCheck {
  status: QualityStatus;
  warnings: string[];
  repetition_score: number;
  repetition_fixed: boolean;
}

export interface GenerationOutput {
  channel: Channel;
  language: string;
  email: EmailCopy;
  mobile: MobileCopy;
  sms: SmsCopy;
  quality: QualityCheck;
  grounded: boolean;
  provider: string;
  models: Record<string, string | null>;
}

export interface AgentExecution {
  id: number;
  generation_id: number;
  agent_name: string;
  title: string;
  description: string;
  sequence: number;
  status: AgentStatus;
  input_summary: string | null;
  output_json: Record<string, unknown> | null;
  error_message: string | null;
  model_name: string | null;
  duration_ms: number | null;
  started_at: string | null;
  completed_at: string | null;
}

export interface GroundingSource {
  id: number;
  title: string;
  url: string;
  source_type: string;
  snippet: string | null;
  retrieved_at: string | null;
}

export interface GenerationSummary {
  id: number;
  title: string;
  brief: string;
  channel: Channel;
  language: string;
  status: GenerationStatus;
  grounded: boolean;
  execution_time_ms: number | null;
  brand_name: string | null;
  product_name: string | null;
  audience_segment_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface GenerationDetail extends GenerationSummary {
  user_id: number;
  brand_id: number | null;
  product_id: number | null;
  audience_segment_id: number | null;
  output: GenerationOutput | null;
  provider: string | null;
  error_code: string | null;
  error_message: string | null;
  agent_executions: AgentExecution[];
  grounding_sources: GroundingSource[];
}

export interface GenerationStatusResponse {
  id: number;
  status: GenerationStatus;
  progress: number;
  execution_time_ms: number | null;
  error_code: string | null;
  error_message: string | null;
  steps: AgentExecution[];
  output: GenerationOutput | null;
}

export interface GenerationCreatePayload {
  brief: string;
  channel: Channel;
  brand_id?: number | null;
  product_id?: number | null;
  audience_segment_id?: number | null;
  language?: string;
  title?: string | null;
}

export interface Brand {
  id: number;
  name: string;
  description: string | null;
  guidelines: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Product {
  id: number;
  brand_id: number;
  brand_name: string | null;
  name: string;
  sku: string | null;
  description: string | null;
  features: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AudienceSegment {
  id: number;
  name: string;
  description: string | null;
  tone_guidance: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CtaRule {
  id: number;
  brand_id: number | null;
  product_id: number | null;
  channel: Channel | null;
  template: string;
  priority: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Template {
  id: number;
  name: string;
  channel: Channel;
  description: string | null;
  prompt_template: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ChannelInfo {
  value: Channel;
  label: string;
  description: string;
  fields: string[];
}

export interface DashboardSummary {
  copies_generated_this_month: number;
  copies_generated_total: number;
  audience_segments_configured: number;
  channels_supported: number;
  average_generation_time_ms: number | null;
  success_rate: number;
  channels: ChannelInfo[];
  generations_by_channel: Record<string, number>;
  generations_by_status: Record<string, number>;
}

export interface SystemInfo {
  app_name: string;
  app_version: string;
  environment: string;
  ai_provider: string;
  grounding_enabled: boolean;
  grounding_provider: string;
  models: Record<string, string | null>;
  channel_limits: Record<string, Record<string, number>>;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface ApiErrorPayload {
  error: {
    code: string;
    message: string;
    details: unknown;
    request_id: string | null;
  };
}
