# OpenTelemetry Instrumentation Guide for AI Coding Agents

**Target Audience**: AI Coding Agents (Claude Code, Copilot, etc.)  
**Purpose**: Language-agnostic instrumentation principles with OpenTelemetry best practices

## Main Goal of Instrumentation

**Instrumentation exists to enable humans and agents to understand application behavior at runtime, primarily when debugging issues (errors, anomalies, performance degradations) in production environments.**

Key principles:
- **Concise but precise**: Every telemetry signal should be meaningful and actionable
- **Value-driven**: Each data point and attribute must provide debugging value
- **Noise reduction**: Avoid generating excessive information that obscures insights
- **Production focus**: Design telemetry for production debugging, not development convenience

Remember: The cost of telemetry is not just performance overhead but also cognitive load. Every span, metric, and attribute should answer the question: "Will this help someone debug a production issue?"

## Instrument the Unexpected, Not the Expected

**Focus on anomalies and deviations from the happy path, except for critical business milestones.**

### What to Instrument

**DO instrument the unexpected:**
- Errors and failures
- Retries and fallbacks
- Cache misses (not hits)
- Slow queries (above threshold)
- Circuit breaker state changes
- Rate limit hits
- Degraded responses

**DO instrument critical business milestones (even when successful):**
- Payment captured (with amount)
- Order placed (with order ID)
- User account created (with tier)
- Subscription renewed
- Contract signed
- Funds transferred
- **Reasoning**: These events have business/audit value and need positive confirmation

**DON'T instrument routine expected operations:**
- Every validation that passes
- Cache hits (just count them in metrics)
- Fast queries
- Normal state transitions
- Internal processing steps

### Examples

**Span Events:**
```
✅ GOOD: "retry attempted", "fallback used", "cache miss"
✅ GOOD: "payment.captured" (amount: $500), "subscription.renewed" (plan: premium)
❌ BAD:  "user fetched successfully", "cache hit", "validation passed"
```

**Metrics:**
```
✅ GOOD: Counter with cache.hit=true|false dimension
✅ GOOD: Histogram of all durations (normal + slow)
❌ BAD:  Event for every successful operation
```

**Reasoning**: The normal path is expected to work. Instrumentation should help identify when things deviate from normal, not confirm that everything is working as designed.

## Quick Reference

### Core Instrumentation Principles
- **Minimal spans**: Only at application boundaries (HTTP, DB, messaging, RPC)
- **Golden rule**: Either record error OR return error with context, never both
- **UCUM units**: Use proper units like `{attempts}` not `"1"` for metrics
- **Span events**: For transaction-level events, not lifecycle events
- **Safe context**: Always safe to retrieve spans from context without nil checks

### Universal Boundaries
```
HTTP server requests     - Incoming API/web requests
HTTP client requests     - Outgoing HTTP calls
Database operations      - SQL queries, NoSQL operations
Message queue operations - Publish/consume messages
RPC calls               - gRPC, JSON-RPC, etc.
Cache operations        - Redis, Memcached interactions
External API calls      - Third-party service calls
File I/O operations     - Only for network filesystems
```

### Instrumentation Priority

**High-value instrumentation** (focus here):
- Business operations: checkout, payment, user registration
- Revenue-impacting endpoints: order processing, billing
- User-facing APIs: search, product catalog, authentication
- Critical data pipelines: ETL jobs, event processing

**Low-value instrumentation** (skip or minimize):
- Health checks: /health, /readiness, /liveness
- Internal endpoints: /metrics, /pprof, /debug
- Static assets: CSS, JS, images
- Admin endpoints: Unless critical for operations

**Reasoning**: Instrumentation should focus on understanding business impact and user experience. Internal endpoints add noise without providing debugging value for production issues.

## Span Creation Rules

### Application Boundaries (Create Spans)
Create spans only at these application boundaries when no instrumentation library is available:

```
HTTP Server:  {method} {route}        SpanKind: Server
HTTP Client:  {method}                SpanKind: Client  
Database:     {operation} {table}     SpanKind: Client
Messaging:    {operation} {queue}     SpanKind: Producer/Consumer
RPC:          {service}/{method}       SpanKind: Client/Server
Cache:        {operation} {key_pattern} SpanKind: Client
```

### Anti-Patterns (Never Create Spans)
```
Internal function calls    - Business logic methods
Utility functions         - Helpers, formatters, validators
Loop iterations          - Use events for item-level tracking
Pure computations        - Hash functions, calculations
Memory operations        - Local caching, in-memory processing
Constructor/destructors  - Object lifecycle methods
```

## Error Handling Golden Rule

**Rule**: Error handling depends on span ownership and whether processing continues.

### Correct Patterns

**Pattern 1: You create the span + return error**
```
When you create a span AND return an error:
  - Record the error to YOUR span
  - Set span status to error
  - Return the error to caller
  - Reasoning: You own the span, you must record what happened
```

**Pattern 2: You receive a span + return error**
```
When using existing span (from context) AND return error:
  - Do NOT record the error
  - Return error with context
  - Let span owner handle recording
  - Reasoning: Don't duplicate error recording in the trace
```

**Pattern 3: Error occurs but processing continues**
```
When error occurs during batch/partial processing:
  - Record error to current span (as event or RecordError)
  - Continue processing remaining items
  - Reasoning: Error is handled, not propagated
```

### Wrong Patterns
```
❌ Recording error in child function when returning to parent
❌ Not recording error in span you created before returning
❌ Swallowing errors without recording anywhere
❌ Creating spans just for error handling
```

## Metrics Best Practices

### UCUM Units and Naming
```
Counts:     {things}      - Not "1" or "count"
Duration:   ms, s         - Milliseconds, seconds
Size:       By, KiBy      - Bytes, kilobytes  
Rate:       {things}/s    - Things per second
Percentage: %             - Percent (0-100)
Ratio:      1             - Ratio (0-1)
```

### Metric Types
```
Counter:    Monotonically increasing values
  - Total requests, errors, bytes sent
  
Histogram:  Distribution of values
  - Request duration, payload size
  
Gauge:      Point-in-time values
  - Active connections, queue depth
  
UpDownCounter: Values that increase/decrease
  - Active requests, items in cache
```

### Cardinality Management
```
✅ LOW: Status codes, methods, endpoints (< 100 values)
⚠️ MEDIUM: Customer tiers, regions (< 1000 values)  
❌ HIGH: User IDs, request IDs, timestamps (unbounded)
```

## Logging vs Span Events

### Logging: Lifecycle Events Only
```
Application startup/shutdown
Configuration changes
Circuit breaker state changes
Resource pool changes
Background job scheduling
Critical system errors
```

**Important**: Application startup spans must be closed BEFORE the application blocks waiting for shutdown signals. Otherwise, the span will remain open for the entire application lifetime, providing no value.

```
CORRECT:
1. Start application initialization span
2. Initialize components (DB, HTTP server, etc.)
3. Close initialization span
4. Block waiting for shutdown signal
5. On shutdown: create new span for graceful shutdown

WRONG:
1. Start application span
2. Initialize components
3. Block waiting for signal (span still open!)
4. Close span on shutdown (span duration = entire app lifetime)
```

### Span Events: Transaction-Level Anomalies
```
Unexpected paths within request:
- Retry attempts (not first try success)
- Cache misses (not hits)
- Fallback activation
- Partial failures in batch processing
- Authorization denials (not approvals)
- Slow operations above threshold
- Resource exhaustion
```

### Decision Matrix
```
Within transaction boundary?  → Use span event
Application lifecycle?        → Use logging
Debug information?           → Use span attributes
Performance metric?          → Use metrics
```

## Context and Attribute Management

### Standard Attribute Categories
```
Identity:    user.id, tenant.id, session.id
Business:    order.id, product.sku, transaction.type
Technical:   cache.hit, retry.attempt, queue.depth
Environment: deployment.environment, service.version
```

### Attribute Guidelines
```
✅ DO:
- Add attributes to existing spans
- Use semantic conventions when available
- Keep cardinality low for attribute values
- Add business context for observability

❌ DON'T:
- Create spans just to add attributes
- Include PII without encryption
- Use high-cardinality values as attributes
- Duplicate information across multiple attributes
```

## Library Instrumentation

### Detection Strategy
```
1. Check for existing instrumentation libraries
2. Look for middleware/interceptor patterns
3. Verify auto-instrumentation availability
4. Only create manual spans if none exist
```

### Common Instrumentation Libraries
```
HTTP:       OpenTelemetry HTTP instrumentation
Database:   OpenTelemetry SQL/NoSQL instrumentation  
Messaging:  OpenTelemetry messaging instrumentation
RPC:        OpenTelemetry RPC instrumentation
Cache:      OpenTelemetry cache instrumentation
```

### Manual Instrumentation Rules
```
IF instrumentation_library_exists:
    USE library instrumentation
    ADD business attributes only
ELSE:
    CREATE boundary spans only
    FOLLOW semantic conventions
    INCLUDE standard attributes
```

## Semantic Conventions

### Version Management
```
- Use latest stable version consistently
- Import once, use everywhere
- Document version in dependencies
- Update across entire codebase
```

### Standard Domains
```
http.*       - HTTP protocol attributes
db.*         - Database attributes
rpc.*        - RPC attributes
messaging.*  - Messaging attributes
faas.*       - Function-as-a-Service attributes
cloud.*      - Cloud provider attributes
container.*  - Container attributes
k8s.*        - Kubernetes attributes
```

## Implementation Patterns

### HTTP Pattern
```
When instrumented:
  - Span already exists from library
  - Add business attributes only
  - Use existing span for events

When not instrumented:
  - Create span with Server/Client kind
  - Add semantic convention attributes
  - Handle errors appropriately
```

### Database Pattern
```
Span name:   {operation} {table}
Attributes:  db.system, db.name, db.operation
Events:      Query retries, connection pool events
Errors:      Classify (timeout, constraint, connection)
```

### Message Queue Pattern
```
Producer:    send {destination}
Consumer:    receive {destination}
Attributes:  messaging.system, messaging.destination
Events:      Message published, processing milestones
```

### Background Job Pattern
```
Span name:   {job_type}
Attributes:  job.id, job.scheduled_at, batch.size
Events:      Item processing, checkpoints
Metrics:     Items processed, duration, failures
```

## SLO and SLI Recommendations

When reviewing instrumentation for an application, identify appropriate SLOs (Service Level Objectives) and the SLIs (Service Level Indicators) that will measure them.

### Common SLO Patterns and Their SLIs

#### Availability SLO
**SLO**: "99.9% of requests should return successfully"
**SLIs**:
- Success rate: `(total_requests - error_requests) / total_requests`
- Metric: HTTP status codes < 500
- Reasoning: User-facing errors (4xx) are not availability issues

#### Latency SLO  
**SLO**: "95% of requests should complete within 200ms"
**SLIs**:
- P95 latency from request duration histograms
- Measured at application boundary (HTTP handler)
- Reasoning: P95 captures typical user experience while tolerating outliers

#### Data Freshness SLO
**SLO**: "95% of events processed within 5 minutes"
**SLIs**:
- Time between event creation and processing completion
- Metric: `processing_timestamp - event_timestamp`
- Reasoning: Critical for real-time data pipelines

#### Error Budget SLO
**SLO**: "Less than 0.1% error rate for critical transactions"
**SLIs**:
- Error rate per transaction type
- Classify errors: user errors vs system errors
- Reasoning: Focus on system errors that impact user experience

### Choosing SLOs Based on Application Type

#### API Services
- **Availability**: 99.9% success rate
- **Latency**: P99 < 500ms
- **Reasoning**: APIs need consistent performance and high availability

#### Batch Processing
- **Completeness**: 100% of items processed
- **Timeliness**: 95% completed within SLA window
- **Reasoning**: Batch jobs prioritize completeness over latency

#### Real-time Systems
- **Latency**: P99 < 100ms
- **Throughput**: Process X events/second
- **Reasoning**: Real-time systems require strict latency guarantees

#### Background Jobs
- **Success Rate**: 99.9% eventual success (with retries)
- **Processing Time**: P95 within expected duration
- **Reasoning**: Background jobs can retry, so eventual success matters most

### SLI Implementation Requirements

For each SLI, ensure:
1. **Metrics exist** at the right boundaries
2. **Attributes** distinguish critical vs non-critical operations
3. **Error classification** separates user errors from system errors
4. **Business context** identifies transaction types
5. **Aggregation level** matches user experience

## Implementation Checklist

### SLO/SLI Validation
- [ ] Identified appropriate SLOs for application type
- [ ] Selected measurable SLIs for each SLO
- [ ] **IMPORTANT**: Do NOT add metrics unless explicitly requested by user
- [ ] Recommend which metrics would support SLIs (without implementing)
- [ ] Verify if existing instrumentation can support proposed SLIs
- [ ] Error classification supports SLI calculation
- [ ] Business attributes enable segmentation

### Span Validation
- [ ] Spans at boundaries only
- [ ] Proper span kinds used
- [ ] Semantic conventions followed
- [ ] Business context included
- [ ] No internal function spans

### Error Handling
- [ ] Single error handling strategy
- [ ] Errors classified when useful
- [ ] Status set for user operations
- [ ] No double error recording

### Metrics Validation  
- [ ] UCUM units used
- [ ] Cardinality controlled
- [ ] Business metrics included
- [ ] Proper metric types selected

### Context Management
- [ ] Safe context retrieval
- [ ] Low cardinality attributes
- [ ] Business attributes added
- [ ] No PII in clear text

### Library Usage
- [ ] Existing libraries detected
- [ ] Auto-instrumentation used
- [ ] Manual only when necessary
- [ ] Version consistency maintained

## Anti-Patterns to Avoid

### Span Anti-Patterns
- ❌ Creating spans for every function
- ❌ Spans for pure computations
- ❌ Nested spans for internal calls
- ❌ Spans without boundaries

### Error Anti-Patterns
- ❌ Recording and returning errors
- ❌ Silent error swallowing
- ❌ Error-only spans
- ❌ Missing error classification

### Metric Anti-Patterns
- ❌ Wrong units ("1" instead of {things})
- ❌ High cardinality labels
- ❌ Missing business metrics
- ❌ Wrong metric types

### Context Anti-Patterns
- ❌ Nil checking for spans
- ❌ High cardinality attributes
- ❌ PII in attributes
- ❌ Creating spans for attributes

---

**Remember**: This guide focuses on minimal, boundary-based instrumentation that provides maximum observability value with minimal performance impact. Always use existing instrumentation libraries before implementing manual instrumentation.