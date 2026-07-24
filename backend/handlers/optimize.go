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

type OptimizeTeamRequest struct {
	SalaryCap      int      `json:"salary_cap"`
	LockedPlayers  []string `json:"locked_players"`
	ExcludedPlayers []string `json:"excluded_players"`
	PopulationSize int      `json:"population_size"`
	NGenerations   int      `json:"n_generations"`
}

func OptimizeTeam(c *fiber.Ctx) error {
	var body OptimizeTeamRequest
	if err := c.BodyParser(&body); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(&fiber.Map{
			"status":  "Failure",
			"message": "Invalid request body",
		})
	}

	if body.SalaryCap <= 0 {
		body.SalaryCap = 200_000_000
	}
	if body.PopulationSize <= 0 {
		body.PopulationSize = 40
	}
	if body.NGenerations <= 0 {
		body.NGenerations = 60
	}
	if body.LockedPlayers == nil {
		body.LockedPlayers = []string{}
	}
	if body.ExcludedPlayers == nil {
		body.ExcludedPlayers = []string{}
	}

	optimizerURL := os.Getenv("OPTIMIZER_API_URL")
	if optimizerURL == "" {
		optimizerURL = "http://localhost:8005"
	}

	payload, err := json.Marshal(body)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(&fiber.Map{
			"status":  "Failure",
			"message": "Failed to build request",
		})
	}

	client := &http.Client{Timeout: 120 * time.Second}
	resp, err := client.Post(
		fmt.Sprintf("%s/optimize-team", optimizerURL),
		"application/json",
		bytes.NewReader(payload),
	)
	if err != nil {
		return c.Status(fiber.StatusBadGateway).JSON(&fiber.Map{
			"status":  "Failure",
			"message": fmt.Sprintf("Failed to reach optimizer service: %v", err),
		})
	}
	defer resp.Body.Close()

	respBytes, err := io.ReadAll(resp.Body)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(&fiber.Map{
			"status": "Failure",
			"message": "Failed to read optimizer response",
		})
	}

	if resp.StatusCode != http.StatusOK {
		return c.Status(resp.StatusCode).JSON(&fiber.Map{
			"status": "Failure",
			"message": string(respBytes),
		})
	}

	var result map[string]any
	if err := json.Unmarshal(respBytes, &result); err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(&fiber.Map{
			"status": "Failure",
			"message": "Invalid response from optimizer service",
		})
	}

	return c.Status(fiber.StatusOK).JSON(result)
}

func NewOptimizeHandler(router fiber.Router) {
	router.Post("/", OptimizeTeam)
}
