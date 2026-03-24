# 0004 — Invitation-only registration

## Context

Exogram is a social network for readers with a deliberately curated approach.
Community quality and trust between users are a central part of the product.
Open registration could degrade that quality and introduce spam or behaviors
incompatible with the project's culture.

## Decision

The only way to create an account is to be invited by an existing user or
to be activated from the waitlist by a user with available invitations.

**Invitation flow:**
1. A registered user sends an invitation to an email address.
2. The system generates an HMAC-SHA256 token (using `SECRET_KEY` as the key) and sends it by email.
3. The invitee uses the link to complete registration within 72 hours.
4. Upon registering, the invitee is associated with the inviter in the network graph.

**Waitlist:**
1. Anyone can sign up on the waitlist with their email.
2. A registered user can activate someone from the waitlist, consuming one invitation.

**Limits:**
- Each user has a maximum number of invitations (`MAX_INVITATIONS_PER_USER = 10`).
- Invitation tokens expire after 72 hours (`token_created_at` + 72h).
- Tokens use HMAC instead of unsalted SHA256 to resist rainbow table attacks.

**Trust level system:**
New users enter with `comment_allowance_depth = 0`. After 30 days they are automatically
promoted to `depth = 1` via a daily Celery task. This level controls how far into
the social graph they can interact.

## Alternatives considered

**Open registration:** easier for growth, but contradicts the intentional design of
the product. Exogram is not a network for everyone, it is a network for committed readers.

**Invitation-only registration without a waitlist:** leaves out interested people who do not
know a user. The waitlist is the valve: it allows capturing interest and activating
users in a controlled way.

## Consequences

- Growth is slow by design. This is intentional.
- Users have an incentive to invite quality people (their reputation in the graph is associated with their invitees).
- The trust level system allows moderating the participation of new users without manual intervention.
- The 72h expiration requires the email address to be functional. There is no way to recover an expired invitation without the inviter generating a new one.
