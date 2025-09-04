// span_violations_test.go
// Test file with various OpenTelemetry span naming and usage violations
package main

import (
	"context"
	"fmt"
	"time"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/codes"
	"go.opentelemetry.io/otel/trace"
)

var tracer = otel.Tracer("test-violations")

func main() {
	ctx := context.Background()
	
	// Test various span naming violations
	testSpanNamingViolations(ctx)
	testAttributeViolations(ctx)
	testMessagingViolations(ctx)
	testDatabaseViolations(ctx)
	testHTTPViolations(ctx)
}

func testSpanNamingViolations(ctx context.Context) {
	// VIOLATION 1: CamelCase span name
	ctx, span1 := tracer.Start(ctx, "processUserData")
	defer span1.End()
	
	// VIOLATION 2: Mixed case with spaces
	ctx, span2 := tracer.Start(ctx, "Process User Data With Mixed Case")
	defer span2.End()
	
	// VIOLATION 3: Snake case
	ctx, span3 := tracer.Start(ctx, "process_user_data")
	defer span3.End()
	
	// VIOLATION 4: Function name as span
	ctx, span4 := tracer.Start(ctx, "calculateTotals")
	defer span4.End()
	
	// VIOLATION 5: High cardinality with user ID embedded
	userID := "user-12345"
	ctx, span5 := tracer.Start(ctx, "processUser_"+userID)
	defer span5.End()
	
	// VIOLATION 6: Timestamp in span name
	ctx, span6 := tracer.Start(ctx, fmt.Sprintf("operation_%d", time.Now().Unix()))
	defer span6.End()
	
	// VIOLATION 7: All uppercase
	ctx, span7 := tracer.Start(ctx, "PROCESS_ORDER")
	defer span7.End()
	
	// VIOLATION 8: Generic/meaningless name
	ctx, span8 := tracer.Start(ctx, "doSomething")
	defer span8.End()
	
	// VIOLATION 9: Internal function name
	ctx, span9 := tracer.Start(ctx, "validateInput")
	defer span9.End()
	
	// VIOLATION 10: Mixed separators
	ctx, span10 := tracer.Start(ctx, "process-user_data.validation")
	defer span10.End()
}

func testAttributeViolations(ctx context.Context) {
	ctx, span := tracer.Start(ctx, "test attributes")
	defer span.End()
	
	// VIOLATION 11: Uppercase in attribute name
	span.SetAttributes(attribute.String("User.ID", "123"))
	
	// VIOLATION 12: CamelCase attribute
	span.SetAttributes(attribute.String("userEmail", "test@example.com"))
	
	// VIOLATION 13: Mixed case attribute
	span.SetAttributes(attribute.String("Order.Total.Amount", "100"))
	
	// VIOLATION 14: Inconsistent naming
	span.SetAttributes(
		attribute.String("user_id", "123"),
		attribute.String("userId", "123"),  // Different style
		attribute.String("user.id", "123"), // Different style again
	)
	
	// VIOLATION 15: Service name in attribute
	span.SetAttributes(attribute.String("checkoutservice.user.id", "123"))
}

func testMessagingViolations(ctx context.Context) {
	topic := "orders"
	
	// VIOLATION 16: Wrong order - destination first, operation second
	ctx, span1 := tracer.Start(ctx, fmt.Sprintf("%s publish", topic))
	defer span1.End()
	
	// VIOLATION 17: CamelCase in messaging
	ctx, span2 := tracer.Start(ctx, "publishMessage")
	defer span2.End()
	
	// VIOLATION 18: Snake case in messaging
	ctx, span3 := tracer.Start(ctx, "publish_message")
	defer span3.End()
	
	// VIOLATION 19: Generic messaging name
	ctx, span4 := tracer.Start(ctx, "messaging")
	defer span4.End()
}

func testDatabaseViolations(ctx context.Context) {
	// VIOLATION 20: CamelCase in database operation
	ctx, span1 := tracer.Start(ctx, "selectUsers")
	defer span1.End()
	
	// VIOLATION 21: Wrong case
	ctx, span2 := tracer.Start(ctx, "Select Users")
	defer span2.End()
	
	// VIOLATION 22: Missing operation
	ctx, span3 := tracer.Start(ctx, "users")
	defer span3.End()
	
	// VIOLATION 23: Wrong separator
	ctx, span4 := tracer.Start(ctx, "select_users")
	defer span4.End()
}

func testHTTPViolations(ctx context.Context) {
	// VIOLATION 24: CamelCase in HTTP
	ctx, span1 := tracer.Start(ctx, "getUsers")
	defer span1.End()
	
	// VIOLATION 25: Missing path
	ctx, span2 := tracer.Start(ctx, "GET")
	defer span2.End()
	
	// VIOLATION 26: Wrong case for method
	ctx, span3 := tracer.Start(ctx, "get /users")
	defer span3.End()
	
	// VIOLATION 27: Mixed format
	ctx, span4 := tracer.Start(ctx, "GET_USERS")
	defer span4.End()
	
	// VIOLATION 28: High cardinality URL
	userID := "12345"
	ctx, span5 := tracer.Start(ctx, fmt.Sprintf("GET /users/%s", userID))  // Should use template
	defer span5.End()
}

// VIOLATION 29: Creating spans for internal functions (anti-pattern)
func internalCalculation(ctx context.Context, value int) int {
	// This should NOT have a span - it's internal business logic
	ctx, span := tracer.Start(ctx, "internalCalculation")
	defer span.End()
	
	return value * 2
}

// VIOLATION 30: Spans in loops (anti-pattern)
func processItems(ctx context.Context, items []string) {
	for i, item := range items {
		// VIOLATION: Creating span per loop iteration
		ctx, span := tracer.Start(ctx, fmt.Sprintf("processItem_%d", i))
		span.SetAttributes(attribute.String("item", item))
		
		// Simulate work
		time.Sleep(1 * time.Millisecond)
		span.End()
	}
}

// VIOLATION 31: Long-lived application span (anti-pattern)
func applicationLifecycleSpan() {
	ctx := context.Background()
	
	// This span will live for the entire application lifetime - WRONG
	ctx, appSpan := tracer.Start(ctx, "Application Lifecycle")
	defer appSpan.End() // Only ends when app shuts down
	
	// Simulate application work
	for i := 0; i < 10; i++ {
		handleRequest(ctx, fmt.Sprintf("request-%d", i))
	}
}

func handleRequest(ctx context.Context, requestID string) {
	// VIOLATION 32: High cardinality span name with request ID
	ctx, span := tracer.Start(ctx, "handleRequest_"+requestID)
	defer span.End()
	
	// VIOLATION 33: PII in attributes
	span.SetAttributes(
		attribute.String("user.email", "john.doe@sensitive.com"),
		attribute.String("user.ssn", "123-45-6789"),
	)
}

// VIOLATION 34: Error handling violations
func errorHandlingViolations(ctx context.Context) error {
	ctx, span := tracer.Start(ctx, "errorTest")
	defer span.End()
	
	err := fmt.Errorf("simulated error")
	
	// VIOLATION: Recording error AND returning it (double recording)
	span.RecordError(err)
	span.SetStatus(codes.Error, err.Error())
	
	return err // Caller will also record this error - duplication
}

// VIOLATION 35: Using wrong span kinds
func wrongSpanKinds(ctx context.Context) {
	// VIOLATION: Internal function marked as SERVER span
	ctx, span1 := tracer.Start(ctx, "internalWork", trace.WithSpanKind(trace.SpanKindServer))
	defer span1.End()
	
	// VIOLATION: Non-client call marked as CLIENT span  
	ctx, span2 := tracer.Start(ctx, "localComputation", trace.WithSpanKind(trace.SpanKindClient))
	defer span2.End()
}