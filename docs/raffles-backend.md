# BIDALS Raffles Backend Foundation

This document describes the first backend-authoritative raffle foundation. It is intentionally scoped to domain integrity, governance, auditability, and future payment/UI expansion.

## Domain Model

- `SellerRaffleFeature` stores the smallest current feature-gating foundation. `Signature` includes raffles; `Essentials` can enable raffles with `raffles_enabled=True`.
- `RaffleCampaign` is the authoritative raffle container. It can optionally link to an `Auction`, has server-owned timing, capacity, pricing, and a lifecycle status.
- `RafflePrize` stores ordered prizes for a campaign.
- `RafflePurchase` stores payment-completion placeholders and split amounts. It is ready for a future payment webhook to call the service layer.
- `RaffleTicket` stores immutable backend-issued ticket numbers. Ticket numbers are unique per campaign and are never supplied by the frontend.
- `RaffleDraw` stores one successful draw per campaign with randomness metadata.
- `RaffleWinner` stores immutable prize, ticket, and winner assignments.

## Lifecycle

Campaign statuses are:

- `draft`
- `scheduled`
- `live`
- `closed`
- `drawn`
- `cancelled`

Tickets can only be issued while a campaign is `live` and inside its backend sales window. Draws can only run after a campaign is explicitly `closed`. The draw service transitions the campaign to `drawn` after the draw and winner records are created atomically.

## Permissions And Governance

- Bidders can view eligible public raffles, view winners, and read only their own tickets.
- Sellers can create and manage raffles for their own auctions only when raffles are enabled for that seller.
- Sellers cannot buy tickets for their own raffle or their own auction/event.
- Admins can read and perform controlled operational actions, but cannot buy raffle tickets.
- Close and draw operations require seller/admin authority and create audit logs.
- Purchase completion is exposed only through an admin-only backend endpoint and the service layer. It is not a public fake payment flow.

## Feature Flags

Raffle gating is evaluated against `SellerRaffleFeature`:

- `plan_code=signature` enables raffles.
- `plan_code=essentials` requires `raffles_enabled=True`.
- Missing feature settings mean raffles are disabled.

Disabled seller raffles are hidden from bidder-facing list/detail routes. Admins can still read them for support/debug.

## Ticket And Draw Rules

- Ticket issuing is backend-only and sequential within a transaction.
- Ticket numbers are unique per campaign.
- Ticket owner, campaign, purchase, and number are immutable after issue.
- Active tickets can only be issued for completed purchases.
- Draws use `secrets.randbelow` without replacement.
- A campaign can have only one draw.
- A prize can have only one winner.
- One ticket cannot win multiple prizes in the current foundation.
- Winners are immutable after assignment.

## Audit Logging

Raffle actions extend `AuditAction`:

- `raffle_campaign_created`
- `raffle_campaign_updated`
- `raffle_prize_created`
- `raffle_purchase_completed`
- `raffle_tickets_issued`
- `raffle_closed`
- `raffle_draw_executed`
- `raffle_winner_assigned`
- `raffle_cancelled`
- `raffle_outcome_repair_requested`

Audit metadata includes campaign id, auction id, actor id, purchase id, ticket quantity and ranges, prize id, winning ticket id/number, draw id, status changes, and draw metadata. Payment secrets are not logged.

## Intentionally Not Included Yet

- Real payment processor integration.
- Legal/licence enforcement.
- Public raffle UI.
- Payout, settlement, or charity disbursement automation.
- Raffle outcome repair workflow beyond reserving the audit taxonomy action.
