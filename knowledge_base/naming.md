# OpenTelemetry Naming Guide for AI Coding Agents

**Target Audience**: AI Coding Agents (Claude Code, Copilot, etc.)  
**Purpose**: Automated instrumentation with consistent OpenTelemetry naming

## Quick Reference

### Core Naming Principles
- **Span Names**: Follow `{verb} {object}` pattern (e.g., `GET /users`, `SELECT orders`)
- **Metric Names**: Follow hierarchical `{domain}.{component}.{property}` pattern (e.g., `http.server.request.duration`)
  - Never include service name or company name in metric names
- **Attribute Names**: Hierarchical lowercase with snake_case (e.g., `http.request.method`)
- **Low Cardinality**: Never include user IDs, timestamps, or unique identifiers
- **Constants**: Define all names as constants for reusability across modules

### Universal Properties
```
.name     - Human-readable identifiers (service.name, container.name)
.id       - System identifiers (container.id, process.pid) 
.version  - Version information (service.version, network.protocol.version)
.type     - Classification (messaging.operation.type, error.type)
.address  - Network addresses (server.address, client.address)
.port     - Port numbers (server.port, client.port)
.size     - Byte measurements (http.request.body.size)
.count    - Quantities (messaging.batch.message_count)
.duration - Time measurements (http.server.request.duration)
```

## Constants and Reusability

### Project-Wide Constants
Define these as project-wide constants for cross-service consistency:
```
tenant.id          - Multi-tenant applications
user.id            - User identification 
organization.id    - Organization/company identification
session.id         - User session tracking
request.id         - Request correlation
```

### Language-Agnostic Constant Naming
- **Go**: `const TenantID = "tenant.id"`
- **Java**: `public static final String TENANT_ID = "tenant.id";`
- **JavaScript**: `const TENANT_ID = 'tenant.id';`
- **Python**: `TENANT_ID = "tenant.id"`
- **C#**: `public const string TenantId = "tenant.id";`

### Documentation Requirements
Each constant should include:
- Usage context
- Expected cardinality (low/medium/high)
- Examples of valid values
- Cross-service compatibility notes

## Attribute Naming Rules

### Core Domains (Stable)
```
service.*    - Service identity and metadata
process.*    - Operating system processes  
container.*  - Container runtime information
host.*       - Host/machine information
cloud.*      - Cloud provider metadata
http.*       - HTTP protocol specifics
network.*    - Network layer information
rpc.*        - Remote procedure call attributes
messaging.*  - Message queue systems
db.*         - Database operations
url.*        - URL components
```

### Property Patterns
```
*.address / *.port           - Network endpoints
*.size / *.count / *.duration - Measurements
*.state / *.status / *.status_code - Status information
*.local.* / *.peer.*         - Network perspective
*.client.* / *.server.*      - Communication side
```

### Template Attributes (Dynamic Keys)
```
http.request.header.{key}           - HTTP headers
k8s.pod.label.{key}                 - Kubernetes labels  
container.label.{key}               - Container labels
process.environment_variable.{key}  - Environment variables
```

### System-Specific Namespacing
```
{system}.{property}
aws.s3.key                 - AWS S3 specific
cassandra.consistency.level - Database specific
signalr.connection.status   - Protocol specific
```

## Span Naming Rules

**Core Pattern**: `{verb} {object}` - Action followed by what's being acted upon

### HTTP Spans
```
Format: {method} {route} OR {method}
Examples:
  "GET /api/users/{id}"  (verb: GET, object: /api/users/{id})
  "POST /api/orders"     (verb: POST, object: /api/orders) 
  "GET"                  (verb only when route unknown)

Constants:
  HTTP_GET = "GET"
  HTTP_POST = "POST"
  API_USERS_ROUTE = "/api/users/{id}"
```

### Database Spans
```
Priority: {db.query.summary} > {operation} {target} > {target} > {system}
Examples:
  "SELECT users"         (verb: SELECT, object: users)
  "INSERT user_table"    (verb: INSERT, object: user_table)
  "user_profiles"        (object only when operation unknown)
  "postgresql"           (system fallback)

Constants:
  DB_SELECT = "SELECT"
  DB_INSERT = "INSERT"
  TABLE_USERS = "users"
```

### RPC Spans
```
Format: $package.$service/$method (full qualified name)
Examples:
  "grpc.test.EchoService/Echo"
  "com.example.PaymentService/ProcessPayment"

Constants:
  PAYMENT_SERVICE = "com.example.PaymentService"
  PROCESS_PAYMENT_METHOD = "ProcessPayment"
  PAYMENT_RPC = PAYMENT_SERVICE + "/" + PROCESS_PAYMENT_METHOD
```

### Messaging Spans
```
Format: {operation} {destination}
Examples:
  "send queue.orders"              (verb: send, object: queue.orders)
  "receive topic.user-events"      (verb: receive, object: topic.user-events)
  "publish exchange.notifications" (verb: publish, object: exchange.notifications)

Constants:
  MSG_SEND = "send"
  MSG_RECEIVE = "receive"
  QUEUE_ORDERS = "queue.orders"
```

### Generative AI Spans
```
Format: {operation} {model}
Examples:
  "chat gpt-4"                  (verb: chat, object: gpt-4)
  "generate_content gemini-pro" (verb: generate_content, object: gemini-pro)
  "text_completion davinci-003" (verb: text_completion, object: davinci-003)

Constants:
  AI_CHAT = "chat"
  AI_GENERATE_CONTENT = "generate_content"
  MODEL_GPT4 = "gpt-4"
```

## Metric Naming Rules

**Core Pattern**: Hierarchical `{domain}.{component}.{property}` - NO service/company names

### HTTP Metrics
```
http.server.request.duration  - Server request duration
http.client.request.duration  - Client request duration

✅ CORRECT: http.server.request.duration
❌ WRONG: mycompany.http.server.request.duration
❌ WRONG: userservice.http.server.request.duration

Constants:
  HTTP_SERVER_DURATION = "http.server.request.duration"
  HTTP_CLIENT_DURATION = "http.client.request.duration"
```

### Database Metrics
```
db.client.operation.duration  - Database operation duration

✅ CORRECT: db.client.operation.duration  
❌ WRONG: myapp.db.client.operation.duration

Constants:
  DB_OPERATION_DURATION = "db.client.operation.duration"
```

### Messaging Metrics
```
messaging.client.operation.duration    - Messaging operation duration
messaging.client.sent.messages         - Messages sent count
messaging.client.received.messages     - Messages received count

✅ CORRECT: messaging.client.sent.messages
❌ WRONG: orderservice.messaging.client.sent.messages

Constants:
  MSG_OPERATION_DURATION = "messaging.client.operation.duration"
  MSG_SENT_COUNT = "messaging.client.sent.messages"
```

### System Metrics
```
system.cpu.time         - CPU time by mode
system.memory.usage     - Memory usage
system.network.io       - Network I/O

✅ CORRECT: system.cpu.time
❌ WRONG: mycompany.system.cpu.time

Constants:
  SYSTEM_CPU_TIME = "system.cpu.time"
  SYSTEM_MEMORY_USAGE = "system.memory.usage"
```

## Implementation Checklist

### Validation Rules
- [ ] Span names follow `{verb} {object}` pattern
- [ ] Metric names follow `{domain}.{component}.{property}` hierarchy
- [ ] Metrics DO NOT include service/company names
- [ ] Attribute names are lowercase with snake_case for multi-words
- [ ] High-cardinality values avoided in names
- [ ] Constants defined for reusable names
- [ ] Cross-service attributes use project-wide constants

### Anti-Patterns to Avoid
- ❌ `http.request.url` (high cardinality - use route template)
- ❌ `user.john.doe.action` (user-specific naming)
- ❌ `request.2024-01-15.data` (timestamp in name)
- ❌ `CamelCase.attribute.Name` (wrong case)
- ❌ `myservice.http.server.duration` (service name in metric)
- ❌ `acmecorp.db.client.duration` (company name in metric)
- ❌ Hardcoded strings instead of constants

### Context-Aware Logic
```
if (hasRoute && isLowCardinality(route)) {
    spanName = method + " " + route
} else {
    spanName = method
}

if (hasQuerySummary) {
    spanName = querySummary
} else if (hasOperation && hasTarget) {
    spanName = operation + " " + target
} else if (hasTarget) {
    spanName = target
} else {
    spanName = dbSystem
}
```

### Cardinality Monitoring
- Monitor unique span names per service (target: < 100)
- Monitor unique attribute values (target: < 1000 per attribute)
- Alert on sudden cardinality increases
- Regular cardinality audits for new instrumentation

### Constants Management Strategy
- Group constants by domain (HTTP_*, DB_*, MSG_*)
- Version constants with breaking changes
- Document cross-service dependencies
- Validate constant usage in CI/CD
- Generate constants from OpenTelemetry semantic conventions

---

**Remember**: This guide prioritizes consistency and maintainability. When in doubt, follow existing OpenTelemetry semantic conventions and always use constants for reusable names.