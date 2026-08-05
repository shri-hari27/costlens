# Build stage
FROM golang:1.25-alpine AS builder

WORKDIR /app

COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o costlens-backend .

# Final stage - distroless, minimal attack surface
FROM gcr.io/distroless/static-debian12

WORKDIR /app

COPY --from=builder /app/costlens-backend .
COPY --from=builder /app/static ./static

EXPOSE 8080

ENTRYPOINT ["/app/costlens-backend"]
