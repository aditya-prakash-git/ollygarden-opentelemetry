// test.go
// Intentionally bad OpenTelemetry instrumentation for validator testing.
package main

import (
	"context"
	"errors"
	"fmt"
	"log"
	"math/rand"
	"time"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/codes"
	"go.opentelemetry.io/otel/trace"
)

// Global tracer (copied pattern from main.go style, but misused below)
var badTracer = otel.Tracer("checkout-test")

// VIOLATION: App-lifetime span (kept open across the whole process)
func main() {
	ctx := context.Background()
	ctx, appSpan := badTracer.Start(ctx, "Application Startup And Run Forever") // wrong name & lifetime
	defer appSpan.End()                                                         // ends at exit; span will be huge

	// VIOLATION: high-cardinality attributes on long-lived span
	appSpan.SetAttributes(
		attribute.String("user.id", fmt.Sprintf("user-%d", rand.Int())), // high cardinality
		attribute.String("request.id", fmt.Sprintf("req-%d", time.Now().UnixNano())),
	)

	// Simulate a request handler
	for i := 0; i < 2; i++ {
		if err := handleCheckout(ctx, fmt.Sprintf("user-%d", i)); err != nil {
			// VIOLATION: duplicate error recording at caller + callee
			appSpan.RecordError(err)
			appSpan.SetStatus(codes.Error, err.Error())
			log.Printf("error bubbled to main: %v", err)
		}
	}
}

// Pretend this is analogous to PlaceOrder but intentionally bad.
func handleCheckout(ctx context.Context, userID string) error {
	// VIOLATION: span for internal business logic, wrong naming pattern
	ctx, span := badTracer.Start(ctx, "HandleCheckoutInternalBusiness") // not a boundary; CamelCase; not {verb} {object}
	defer span.End()

	// VIOLATION: high-cardinality name-like attribute
	span.SetAttributes(attribute.String("app.user.id", userID)) // should be added to an existing boundary span only

	// VIOLATION: routine/expected operation as span event
	span.AddEvent("cache hit", trace.WithAttributes(attribute.Bool("cache.hit", true)))

	// Nested internal spans (anti-pattern)
	if err := computeTotals(ctx, userID); err != nil {
		// VIOLATION: duplicate error recording (callee also records)
		span.RecordError(err)
		span.SetStatus(codes.Error, "computeTotals failed: "+err.Error())
		return err
	}

	// Another internal function needlessly wrapped with its own span
	if err := chargeCardInternal(ctx, userID, 1999); err != nil {
		span.RecordError(err)
		span.SetStatus(codes.Error, "chargeCardInternal failed: "+err.Error())
		return err
	}

	// VIOLATION: event for expected success (noise)
	span.AddEvent("user fetched successfully")

	return nil
}

func computeTotals(ctx context.Context, userID string) error {
	// VIOLATION: span for pure computation
	ctx, span := badTracer.Start(ctx, "ComputeTotalsFor_"+userID) // embeds userID (high cardinality)
	defer span.End()

	// VIOLATION: wrong attribute casing & semantics
	span.SetAttributes(
		attribute.String("Order.ID", fmt.Sprintf("ord-%d", time.Now().UnixNano())), // CamelCase key; high cardinality value
	)

	// Simulate partial failure
	if rand.Intn(2) == 0 {
		err := errors.New("price lookup timeout")
		// VIOLATION: returns error AND records here (caller will also record)
		span.RecordError(err)
		span.SetStatus(codes.Error, "lookup failed")
		return err
	}

	// VIOLATION: lifecycle-ish info as span event
	span.AddEvent("configuration loaded", trace.WithAttributes(attribute.String("env", "dev")))
	return nil
}

func chargeCardInternal(ctx context.Context, userID string, cents int) error {
	// VIOLATION: wrong kind & wrong {verb} {object} pattern; not a boundary
	ctx, span := badTracer.Start(ctx, "Payment.ProcessCard_"+userID, trace.WithSpanKind(trace.SpanKindClient))
	defer span.End()

	// VIOLATION: high-cardinality / PII-ish attribute
	span.SetAttributes(
		attribute.String("customer.email", userID+"@example.com"),
		attribute.Int("amount.cents", cents),
	)

	// Simulate downstream call error, but this function owns the span and ALSO re-returns error (OK),
	// we'll add extra violations below.
	if rand.Intn(3) == 0 {
		err := errors.New("bank declined")
		// VIOLATION: add both event and status redundantly for the same error
		span.AddEvent("error", trace.WithAttributes(attribute.String("message", err.Error())))
		span.RecordError(err)
		span.SetStatus(codes.Error, "bank declined")

		// VIOLATION: noisy success counter as event for the next call (nonsense)
		span.AddEvent("request completed successfully")

		return err
	}

	// VIOLATION: success span with needlessly specific/hardcoded name values in attributes
	span.SetAttributes(
		attribute.String("payment.status", "APPROVED_OK_200_SUCCESS"), // verbose, not useful
	)
	return nil
}

// Another useless nested span for a loop (anti-pattern)
func iterateItems(ctx context.Context, items []string) {
	for _, it := range items {
		func(ctx context.Context, item string) {
			// VIOLATION: span per loop item
			ctx, span := badTracer.Start(ctx, "LoopItem:"+item)
			defer span.End()

			// VIOLATION: timestamp in attribute value (cardinality explosion)
			span.SetAttributes(attribute.String("ts", time.Now().Format(time.RFC3339Nano)))
		}(ctx, it)
	}
}
