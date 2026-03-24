package controller

import (
	"math"
	"regexp"
	"strings"
)

var negationMarkers = []string{"不", "没", "不是", "不会", "never", "not", "no "}
var preferenceMarkers = []string{"喜欢", "偏好", "prefer", "prefers", "using", "uses", "选择", "selected"}
var normalizePattern = regexp.MustCompile(`[\p{Han}\w]+`)

func ContradictionConfidence(left string, right string, similarity float64) float64 {
	leftNorm := normalize(left)
	rightNorm := normalize(right)
	ratio := similarityRatio(leftNorm, rightNorm)
	leftNegative := containsAny(leftNorm, negationMarkers)
	rightNegative := containsAny(rightNorm, negationMarkers)
	polarityBonus := 0.0
	if leftNegative != rightNegative {
		polarityBonus = 0.25
	}
	preferenceBonus := 0.0
	if containsAny(leftNorm, preferenceMarkers) || containsAny(rightNorm, preferenceMarkers) {
		preferenceBonus = 0.15
	}
	value := similarity*0.45 + ratio*0.25 + polarityBonus + preferenceBonus
	if value > 1 {
		return 1
	}
	return value
}

func containsAny(text string, values []string) bool {
	for _, value := range values {
		if strings.Contains(text, value) {
			return true
		}
	}
	return false
}

func normalize(text string) string {
	return strings.Join(normalizePattern.FindAllString(strings.ToLower(text), -1), " ")
}

func similarityRatio(left string, right string) float64 {
	if left == right {
		return 1
	}
	if left == "" || right == "" {
		return 0
	}
	leftTokens := strings.Fields(left)
	rightTokens := strings.Fields(right)
	longest := math.Max(float64(len(leftTokens)), float64(len(rightTokens)))
	if longest == 0 {
		return 0
	}
	shared := 0
	seen := map[string]bool{}
	for _, token := range leftTokens {
		seen[token] = true
	}
	for _, token := range rightTokens {
		if seen[token] {
			shared++
		}
	}
	return float64(shared) / longest
}
