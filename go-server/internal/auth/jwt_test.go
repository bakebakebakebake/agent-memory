package auth

import (
	"testing"
	"time"

	"github.com/golang-jwt/jwt/v5"
)

func TestParseBearerToken(t *testing.T) {
	if token := ParseBearerToken("Bearer signed-token"); token != "signed-token" {
		t.Fatalf("unexpected token: %q", token)
	}
	if token := ParseBearerToken(""); token != "" {
		t.Fatalf("expected empty token, got %q", token)
	}
}

func TestJWTMatches(t *testing.T) {
	if !JWTMatches("", "") {
		t.Fatal("expected empty secret to allow passthrough")
	}

	token := jwt.NewWithClaims(jwt.SigningMethodHS256, jwt.RegisteredClaims{
		Subject:   "tester",
		ExpiresAt: jwt.NewNumericDate(time.Now().Add(time.Hour)),
	})
	signed, err := token.SignedString([]byte("secret"))
	if err != nil {
		t.Fatal(err)
	}
	if !JWTMatches(signed, "secret") {
		t.Fatal("expected valid signed jwt to match")
	}
	if JWTMatches(signed, "wrong-secret") {
		t.Fatal("expected wrong secret to fail")
	}

	expired := jwt.NewWithClaims(jwt.SigningMethodHS256, jwt.RegisteredClaims{
		Subject:   "tester",
		ExpiresAt: jwt.NewNumericDate(time.Now().Add(-time.Minute)),
	})
	expiredSigned, err := expired.SignedString([]byte("secret"))
	if err != nil {
		t.Fatal(err)
	}
	if JWTMatches(expiredSigned, "secret") {
		t.Fatal("expected expired token to fail")
	}
	if JWTMatches("", "secret") {
		t.Fatal("expected missing token to fail when secret is required")
	}
}
