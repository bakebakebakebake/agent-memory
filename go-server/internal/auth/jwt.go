package auth

import (
	"errors"
	"net/http"
	"strings"

	"github.com/golang-jwt/jwt/v5"
)

func ParseBearerToken(header string) string {
	if header == "" {
		return ""
	}
	return strings.TrimSpace(strings.TrimPrefix(header, "Bearer"))
}

func JWTMatches(tokenString string, secret string) bool {
	if secret == "" {
		return true
	}
	if tokenString == "" {
		return false
	}
	_, err := jwt.Parse(tokenString, func(token *jwt.Token) (interface{}, error) {
		if token.Method == nil {
			return nil, errors.New("missing signing method")
		}
		return []byte(secret), nil
	})
	return err == nil
}

func HasValidJWT(request *http.Request, secret string) bool {
	return JWTMatches(ParseBearerToken(request.Header.Get("Authorization")), secret)
}
