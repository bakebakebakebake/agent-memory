package auth

import "testing"

func TestAPIKeyMatches(t *testing.T) {
	if !APIKeyMatches("", "") {
		t.Fatal("expected empty expected key to allow passthrough")
	}
	if !APIKeyMatches("good", "good") {
		t.Fatal("expected matching api key to pass")
	}
	if APIKeyMatches("bad", "good") {
		t.Fatal("expected mismatched api key to fail")
	}
}
