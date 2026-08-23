export interface Organization {
  id: string;
  name: string;
  slug: string;
  is_demo: boolean;
}

export interface User {
  id: string;
  organization_id: string;
  email: string;
  full_name: string;
  role: "admin" | "employee";
  is_active: boolean;
  is_demo: boolean;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
  organization: Organization;
}

export interface KnowledgeSource {
  id: string;
  kind: "pdf" | "url" | "text";
  title: string;
  source_url: string | null;
  mime_type: string | null;
  byte_size: number;
  status: "processing" | "ready" | "failed";
  error: string | null;
  chunk_count: number;
  is_demo: boolean;
  created_at: string;
  updated_at: string;
}

export interface Conversation {
  id: string;
  public_reference: string;
  customer_name: string;
  customer_email: string;
  customer_company: string | null;
  subject: string;
  status: string;
  category: string;
  intent: string;
  urgency: string;
  assigned_to_id: string | null;
  is_demo: boolean;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  role: "customer" | "employee" | "internal";
  body: string;
  status: string;
  created_by_id: string | null;
  created_at: string;
}

export interface DraftSource {
  id: string;
  source_id: string;
  chunk_id: string;
  title: string;
  source_url: string | null;
  rank: number;
  score: number;
  quote: string;
}

export interface Draft {
  id: string;
  body: string;
  confidence: number;
  status: "draft" | "approved" | "sent";
  provider: string;
  edited_by_id: string | null;
  approved_by_id: string | null;
  approved_at: string | null;
  sent_at: string | null;
  created_at: string;
  updated_at: string;
  sources: DraftSource[];
}

export interface ConversationDetail extends Conversation {
  messages: Message[];
  draft: Draft | null;
}

export interface Integration {
  id: string;
  kind: "crm" | "workflow";
  provider: "test" | "hubspot" | "n8n";
  enabled: boolean;
  config: Record<string, string | boolean | null>;
  has_secret: boolean;
  last_test_status: string | null;
  last_test_error: string | null;
  is_demo: boolean;
  updated_at: string;
}

export interface CRMRecord {
  id: string;
  conversation_id: string;
  provider: string;
  object_type: string;
  external_id: string;
  payload: Record<string, unknown>;
  is_demo: boolean;
  created_at: string;
}

export interface WebhookDelivery {
  id: string;
  conversation_id: string | null;
  event: string;
  target_url: string;
  status: "pending" | "delivered" | "failed";
  attempt_count: number;
  response_status: number | null;
  response_body: string | null;
  last_error: string | null;
  is_demo: boolean;
  created_at: string;
  last_attempt_at: string | null;
  delivered_at: string | null;
}

export interface ActivityEntry {
  id: string;
  user_id: string | null;
  conversation_id: string | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  level: "info" | "error";
  details: Record<string, unknown>;
  is_demo: boolean;
  created_at: string;
}

export interface Analytics {
  total_conversations: number;
  needs_review: number;
  sent: number;
  escalated: number;
  average_confidence: number;
  webhook_failures: number;
  by_category: Record<string, number>;
  last_seven_days: Array<{ date: string; count: number }>;
}

export interface SendResult {
  conversation: Conversation;
  crm_record: CRMRecord | null;
  webhook_delivery: WebhookDelivery | null;
}

