package handlers

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"time"

	"github.com/gofiber/fiber/v2"
)

type SimulateGameRequest struct {
	TeamID       string `json:"team_id"`
	NFLOpponent  string `json:"nfl_opponent"`
	Season       int    `json:"season"`
	IsHome       bool   `json:"is_home"`
	PlayoffMode  bool   `json:"playoff_mode"`
}

func SimulateGame(c *fiber.Ctx) error {
	var body SimulateGameRequest
	if err := c.BodyParser(&body); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(&fiber.Map{
			"status":  "Failure",
			"message": "Invalid request body",
		})
	}
	if body.TeamID == "" || body.NFLOpponent == "" || body.Season == 0 || body.Season < 2015 || body.Season > 2025 {
		return c.Status(fiber.StatusBadRequest).JSON(&fiber.Map{
			"status":  "Failure",
			"message": "team_id, nfl_opponent, and season are required",
		})
	}

	pythonURL := os.Getenv("SIMULATE_API_URL")
	if pythonURL == "" {
		pythonURL = "http://localhost:8006"
	}

	payload, err := json.Marshal(body)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(&fiber.Map{
			"status":  "Failure",
			"message": "Failed to build request",
		})
	}

	client := &http.Client{Timeout: 60 * time.Second}
	resp, err := client.Post(
		fmt.Sprintf("%s/simulate-game", pythonURL),
		"application/json",
		bytes.NewReader(payload),
	)
	if err != nil {
		return c.Status(fiber.StatusBadGateway).JSON(&fiber.Map{
			"status":  "Failure",
			"message": fmt.Sprintf("Failed to reach simulation service: %v", err),
		})
	}
	defer resp.Body.Close()

	respBytes, err := io.ReadAll(resp.Body)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(&fiber.Map{
			"status":  "Failure",
			"message": "Failed to read simulation response",
		})
	}

	if resp.StatusCode != http.StatusOK {
		return c.Status(resp.StatusCode).JSON(&fiber.Map{
			"status":  "Failure",
			"message": string(respBytes),
		})
	}

	var result map[string]any
	if err := json.Unmarshal(respBytes, &result); err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(&fiber.Map{
			"status":  "Failure",
			"message": "Invalid response from simulation service",
		})
	}

	return c.Status(fiber.StatusOK).JSON(result)
}

func NewSimulateHandler(router fiber.Router) {
	router.Post("/", SimulateGame)
}
