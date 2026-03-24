package auth

import "net/http"

func APIKeyMatches(candidate string, expected string) bool {
	if expected == "" {
		return true
	}
	return candidate == expected
}

func HasAPIKey(request *http.Request, expected string) bool {
	return APIKeyMatches(request.Header.Get("X-API-Key"), expected)
}
