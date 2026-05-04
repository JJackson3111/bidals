export type UserRole = "bidder" | "seller" | "admin";

export type AuctionStatus = "draft" | "scheduled" | "live" | "ended" | "cancelled";
export type LotStatus = "draft" | "open" | "closed" | "sold" | "cancelled";
export type LotWinnerStatus = "pending" | "winner_assigned" | "no_bids" | "reserve_not_met";
export type BidStatus = "accepted" | "rejected";
export type FulfillmentStatus =
  | "pending_confirmation"
  | "winner_confirmed"
  | "seller_contacted"
  | "awaiting_collection_or_delivery"
  | "completed"
  | "cancelled"
  | "disputed";

export type BidRejectionReason =
  | "AUCTION_NOT_LIVE"
  | "LOT_CLOSED"
  | "BID_TOO_LOW"
  | "INVALID_INCREMENT"
  | "USER_NOT_ALLOWED"
  | "UNAUTHENTICATED"
  | "RATE_LIMITED"
  | "SERVER_ERROR";

export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: UserRole;
  is_platform_admin: boolean;
}

export interface Auction {
  id: number;
  title: string;
  description: string;
  start_time: string;
  end_time: string;
  status: AuctionStatus;
  created_by: number;
  created_by_username: string;
  created_at: string;
  updated_at: string;
}

export interface Lot {
  id: number;
  auction: number;
  auction_title: string;
  auction_status: AuctionStatus;
  title: string;
  description: string;
  images: string[];
  starting_price: string;
  reserve_price: string | null;
  current_price: string;
  bid_increment: string;
  status: LotStatus;
  winner: number | null;
  winner_username: string;
  winning_bid: number | null;
  winner_status: LotWinnerStatus;
  winner_calculated_at: string | null;
  uploaded_images: LotImage[];
  created_at: string;
  updated_at: string;
}

export interface LotImage {
  id: number;
  lot: number;
  image: string;
  image_url: string;
  alt_text: string;
  sort_order: number;
  created_at: string;
}

export interface Bid {
  id: number;
  lot: number;
  bidder: number;
  bidder_username: string;
  amount: string;
  status: BidStatus;
  rejection_reason: BidRejectionReason | null;
  server_timestamp: string;
  created_at: string;
}

export interface AuditLog {
  id: number;
  actor: number | null;
  actor_username: string;
  action: string;
  entity_type: string;
  entity_id: string;
  metadata: Record<string, unknown>;
  server_timestamp: string;
}

export type NotificationStatus = "pending" | "sent" | "skipped" | "failed";
export type OutcomeRepairStatus = "pending_review" | "approved" | "rejected" | "applied" | "cancelled";

export interface OutboundNotification {
  id: number;
  recipient: number | null;
  recipient_username: string | null;
  recipient_email: string;
  notification_type: string;
  subject: string;
  status: NotificationStatus;
  related_entity_type: string;
  related_entity_id: string;
  metadata: Record<string, unknown>;
  created_at: string;
  sent_at: string | null;
  read_at: string | null;
  is_read: boolean;
  error_message: string;
}

export interface WinnerReviewItem {
  auction_id: number;
  auction_title: string;
  auction_status: AuctionStatus;
  auction_end_time: string;
  lot_id: number;
  lot_title: string;
  lot_status: LotStatus;
  outcome_status: LotWinnerStatus;
  winner_id: number | null;
  winner_username: string | null;
  winner_email: string | null;
  winning_bid_id: number | null;
  winning_bid_amount: string | null;
  reserve_price: string | null;
  reserve_met: boolean | null;
  calculated_at: string | null;
  fulfillment_id: number | null;
  fulfillment_status: FulfillmentStatus | null;
}

export interface WinnerReviewSummary {
  total_lots: number;
  winner_assigned: number;
  no_bids: number;
  reserve_not_met: number;
}

export interface WinnerReviewResponse {
  summary: WinnerReviewSummary;
  results: WinnerReviewItem[];
}

export interface AuctionResultsResponse extends WinnerReviewResponse {
  auction: Auction;
}

export interface FulfillmentRecord {
  id: number;
  auction: number;
  auction_title: string;
  lot: number;
  lot_title: string;
  lot_status: LotStatus;
  outcome_status: LotWinnerStatus;
  winning_bid: number;
  winning_bid_amount: string;
  winner: number;
  winner_username: string;
  winner_email: string;
  status: FulfillmentStatus;
  confirmation_notes: string;
  seller_notes: string;
  admin_notes: string;
  public_winner_message: string;
  allowed_next_statuses: FulfillmentStatus[];
  last_follow_up_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface FulfillmentSummary {
  total: number;
  pending_confirmation: number;
  winner_confirmed: number;
  seller_contacted: number;
  awaiting_collection_or_delivery: number;
  completed: number;
  cancelled: number;
  disputed: number;
}

export interface FulfillmentResponse {
  summary: FulfillmentSummary;
  results: FulfillmentRecord[];
}

export interface FulfillmentTimelineEvent {
  id: number;
  event_type: string;
  actor_username: string;
  old_status: string | null;
  new_status: string | null;
  notification_type: string;
  note_field?: string;
  attempted_status?: string;
  repair_id?: number | null;
  winning_bid_id?: number | null;
  winner_id?: number | null;
  created_at: string;
}

export interface FulfillmentTimelineResponse {
  results: FulfillmentTimelineEvent[];
}

export type FulfillmentUpdateInput = Partial<Pick<
  FulfillmentRecord,
  "status" | "confirmation_notes" | "seller_notes" | "admin_notes" | "public_winner_message"
>>;

export interface WonLot {
  id: number;
  auction_id: number;
  auction_title: string;
  lot_id: number;
  lot_title: string;
  winning_bid: number;
  winning_bid_amount: string;
  outcome_status: LotWinnerStatus;
  fulfillment_status: FulfillmentStatus;
  public_winner_message: string;
  date_won: string;
  last_follow_up_at: string | null;
  completed_at: string | null;
}

export interface WonLotsResponse {
  results: WonLot[];
}

export interface AccountNotification {
  id: number;
  notification_type: string;
  subject: string;
  body: string;
  status: NotificationStatus;
  related_entity_type: string;
  related_entity_id: string;
  created_at: string;
  sent_at: string | null;
  read_at: string | null;
  is_read: boolean;
}

export interface AccountNotificationsResponse {
  unread_count: number;
  results: AccountNotification[];
}

export interface OutcomeRepairRequest {
  id: number;
  lot: number;
  lot_title: string;
  auction: number;
  auction_title: string;
  current_outcome: LotWinnerStatus;
  requested_winning_bid: number;
  requested_winning_bid_amount: string;
  requested_winner: number;
  requested_winner_username: string;
  reason: string;
  status: OutcomeRepairStatus;
  requested_by: number;
  requested_by_username: string;
  reviewed_by: number | null;
  reviewed_by_username: string | null;
  reviewed_at: string | null;
  approval_notes: string;
  applied_by: number | null;
  applied_by_username: string | null;
  applied_at: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface OutcomeRepairsResponse {
  results: OutcomeRepairRequest[];
}

export interface OutcomeRepairCreateInput {
  lot: number | string;
  requested_winning_bid: number | string;
  reason: string;
}

export interface OutcomeRepairComment {
  id: number;
  repair_request: number;
  author: number;
  author_username: string;
  comment_text: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface OutcomeRepairCommentsResponse {
  results: OutcomeRepairComment[];
}

export interface OutcomeRepairAuditResponse {
  results: AuditLog[];
}

export interface AdminActivityExportParams {
  date_from?: string;
  date_to?: string;
  actor?: string;
  action_type?: string;
  entity_type?: string;
}

export type ReadinessStatus = "PASS" | "WARN" | "FAIL";

export interface ReadinessCheck {
  category: string;
  name: string;
  status: ReadinessStatus;
  message: string;
  details: Record<string, unknown>;
}

export interface ReadinessReport {
  report_type: string;
  generated_at: string;
  environment: string;
  summary: {
    pass: number;
    warn: number;
    fail: number;
  };
  checks: ReadinessCheck[];
  backup_verification?: ReadinessReport;
}

export interface OperationsBidEvent {
  id: number;
  lot_id: number;
  lot_title: string;
  auction_id: number;
  auction_title: string;
  bidder_id: number;
  bidder_username: string;
  amount: string;
  status: BidStatus;
  rejection_reason: BidRejectionReason | null;
  server_timestamp: string;
}

export interface OperationsFailureReason {
  rejection_reason: BidRejectionReason | null;
  count: number;
}

export interface OperationsRepeatedFailure {
  bidder_id: number;
  bidder_username: string;
  rejection_reason: BidRejectionReason | null;
  count: number;
}

export interface OperationsSummary {
  total_bids: number;
  accepted_bids: number;
  rejected_bids: number;
  recent_accepted_bids: number;
  recent_rejected_bids: number;
  recent_audit_events: number;
  recent_server_bid_errors: number;
  suspicious_repeated_failures: number;
  auction_close_runs: number;
  winner_calculations: number;
  bid_anomalies: number;
  alert_events: number;
  job_failures: number;
  notification_events: number;
  pending_notifications: number;
  sent_notifications: number;
  failed_notifications: number;
  skipped_notifications: number;
  fulfillment_pending_confirmation: number;
  fulfillment_seller_contacted: number;
  fulfillment_awaiting_collection_or_delivery: number;
  fulfillment_completed: number;
  fulfillment_disputed: number;
  recent_fulfillment_updates: number;
}

export interface OperationsReport {
  generated_at: string;
  window_minutes: number;
  thresholds: {
    bid_anomaly_reject_threshold: number;
    bid_anomaly_rate_limit_threshold: number;
  };
  summary: OperationsSummary;
  rejected_by_reason: OperationsFailureReason[];
  suspicious_repeated_failures: OperationsRepeatedFailure[];
  recent_accepted_bids: OperationsBidEvent[];
  recent_rejected_bids: OperationsBidEvent[];
  recent_audit_events: AuditLog[];
  recent_server_errors: AuditLog[];
  recent_auction_close_runs: AuditLog[];
  recent_winner_calculations: AuditLog[];
  recent_anomalies: AuditLog[];
  recent_alerts: AuditLog[];
  recent_job_failures: AuditLog[];
  recent_notifications: AuditLog[];
  recent_outbound_notifications: OutboundNotification[];
  recent_failed_notifications: OutboundNotification[];
  recent_fulfillment_updates: AuditLog[];
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface LoginResponse {
  access: string;
  refresh: string;
  user: User;
}

export interface RegisterInput {
  username: string;
  email: string;
  password: string;
  role: "bidder" | "seller";
}

export interface CreateAuctionInput {
  title: string;
  description: string;
  start_time: string;
  end_time: string;
  status: AuctionStatus;
}

export interface CreateLotInput {
  auction: number;
  title: string;
  description: string;
  starting_price: string;
  reserve_price?: string | null;
  bid_increment: string;
  status: LotStatus;
  images?: string[];
}

export type UpdateAuctionInput = Partial<CreateAuctionInput>;
export type UpdateLotInput = Partial<CreateLotInput>;

export interface LotImageOrderItem {
  id: number;
  sort_order: number;
}

export interface BidAcceptedResponse {
  status: "accepted";
  lot_id: number;
  bid_id: number;
  current_price: string;
  server_timestamp: string;
}

export interface BidRejectedResponse {
  status: "rejected";
  lot_id: number;
  reason: BidRejectionReason;
  current_price: string;
  server_timestamp: string;
  message?: string;
  retry_after?: number;
}

export type BidResponse = BidAcceptedResponse | BidRejectedResponse;

export interface ApiErrorBody {
  detail?: string;
  [key: string]: unknown;
}
