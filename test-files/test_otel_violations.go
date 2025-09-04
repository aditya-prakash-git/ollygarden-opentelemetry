package main

import (
    "go.opentelemetry.io/otel"
    "go.opentelemetry.io/otel/attribute"
)

func testViolations() {
    tracer := otel.Tracer("test")
    
    // Should be flagged: camelCase span name
    ctx, span1 := tracer.Start(ctx, "processUserData")
    defer span1.End()
    
    // Should be flagged: snake_case span name  
    ctx, span2 := tracer.Start(ctx, "process_user_data")
    defer span2.End()
    
    // Should be correct: proper HTTP span name
    ctx, span3 := tracer.Start(ctx, "GET /users/{id}")
    defer span3.End()
    
    // Should be correct: proper database span name
    ctx, span4 := tracer.Start(ctx, "SELECT users")
    defer span4.End()
    
    // Attribute tests
    span1.SetAttributes(
        attribute.String("user.id", "123"),           // Correct
        attribute.String("MyServiceName.user", "x"), // Should be flagged
    )
}