# API Key Permissions & Cryptographic Security Model

## Key Classification & Scopes
OmniTriage API keys exist in two distinct functional categories:
1. **Public Publishable Keys (`pk_live_...` / `pk_test_...`):**
   - Safe for client-side inclusion (browsers, mobile applications).
   - Scoped strictly to read-only resource retrieval and telemetry collection.
2. **Secret Server Keys (`sk_live_...` / `sk_test_...`):**
   - Must never be exposed in client bundles or public repositories.
   - Hold granular RBAC scopes: `tickets:write`, `knowledge_base:sync`, `admin:billing`.

## Secret Key Ephemeral Display Policy
For security reasons, full secret keys are displayed exactly ONCE in the administrative dashboard upon creation. OmniTriage stores only salted SHA-256 hashes of secret keys in production databases. 

## Zero Retrieval Policy & Lost Key Rotation
OmniTriage customer support personnel, automated agents, and engineering staff DO NOT possess cryptographic capability to retrieve, decrypt, or email lost secret API keys. If a secret key is compromised or misplaced, administrators must revoke the old key and provision a new key via Settings > Developer > API Keys.
