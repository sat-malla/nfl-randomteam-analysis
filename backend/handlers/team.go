package handlers

import (
	"bytes"
	"context"
	"encoding/json"
	"io"
	"net/http"
	"os"
	"strconv"
	"time"

	"github.com/gofiber/fiber/v2"
	"github.com/sat-malla/nfl-random-team-analysis/backend/models"
)

type teamHandler struct {
	repository models.TeamRepository
}

func (h *teamHandler) GetMany(c *fiber.Ctx) error {
	ctx, cancel := context.WithTimeout(context.Background(), time.Duration(5*time.Second))
	defer cancel()

	teams, err := h.repository.GetMany(ctx)

	if err != nil {
		return c.Status(fiber.StatusBadGateway).JSON(&fiber.Map{
			"status":  "Failure",
			"message": "Failed to fetch teams",
		})
	}

	return c.Status(fiber.StatusOK).JSON(&fiber.Map{
		"status":  "Success",
		"message": "Teams fetched successfully",
		"data":    teams,
	})
}

func (h *teamHandler) GetOne(c *fiber.Ctx) error {
	teamId := c.Params("teamId")

	ctx, cancel := context.WithTimeout(context.Background(), time.Duration(5*time.Second))
	defer cancel()

	team, err := h.repository.GetOne(ctx, teamId)

	if err != nil {
		return c.Status(fiber.StatusBadGateway).JSON(&fiber.Map{
			"status":  "Failure",
			"message": "Failed to fetch team",
		})
	}

	return c.Status(fiber.StatusOK).JSON(&fiber.Map{
		"status":  "Success",
		"message": "Team fetched successfully",
		"data":    team,
	})
}

func (h *teamHandler) CreateOne(c *fiber.Ctx) error {
	team := &models.Team{}

	ctx, cancel := context.WithTimeout(context.Background(), time.Duration(5*time.Second))
	defer cancel()

	if err := c.BodyParser(team); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(&fiber.Map{
			"status":  "Failure",
			"message": "Invalid request body",
		})
	}

	createdTeam, err := h.repository.CreateOne(ctx, *team)

	if err != nil {
		return c.Status(fiber.StatusBadGateway).JSON(&fiber.Map{
			"status":  "Failure",
			"message": "Failed to create team",
		})
	}

	return c.Status(fiber.StatusOK).JSON(&fiber.Map{
		"status":  "Success",
		"message": "Team created successfully",
		"data":    createdTeam,
	})
}

func (h *teamHandler) DeleteOne(c *fiber.Ctx) error {
	teamId, _ := strconv.Atoi(c.Params("teamId"))

	ctx, cancel := context.WithTimeout(context.Background(), time.Duration(5*time.Second))
	defer cancel()

	err := h.repository.DeleteOne(ctx, uint(teamId))

	if err != nil {
		return c.Status(fiber.StatusBadGateway).JSON(&fiber.Map{
			"status":  "Failure",
			"message": "Failed to delete team",
		})
	}

	return c.Status(fiber.StatusOK).JSON(&fiber.Map{
		"status":  "Success",
		"message": "Team deleted successfully",
	})
}

func (h *teamHandler) UpdateOne(c *fiber.Ctx) error {
	teamId, _ := strconv.Atoi(c.Params("teamId"))

	ctx, cancel := context.WithTimeout(context.Background(), time.Duration(5*time.Second))
	defer cancel()

	team := &models.Team{}

	if err := c.BodyParser(team); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(&fiber.Map{
			"status":  "Failure",
			"message": "Invalid request body",
		})
	}

	updatedTeam, err := h.repository.UpdateOne(ctx, uint(teamId), *team)

	if err != nil {
		return c.Status(fiber.StatusBadGateway).JSON(&fiber.Map{
			"status":  "Failure",
			"message": "Failed to update team",
		})
	}

	return c.Status(fiber.StatusOK).JSON(&fiber.Map{
		"status":  "Success",
		"message": "Team updated successfully",
		"data":    updatedTeam,
	})
}

func (h *teamHandler) GetManyByDeviceUuid(c *fiber.Ctx) error {
	deviceUuid := c.Params("deviceUuid")

	ctx, cancel := context.WithTimeout(context.Background(), time.Duration(5*time.Second))
	defer cancel()

	teams, err := h.repository.GetManyByDeviceUuid(ctx, deviceUuid)

	if err != nil {
		return c.Status(fiber.StatusBadGateway).JSON(&fiber.Map{
			"status":  "Failure",
			"message": "Failed to get teams",
		})
	}

	return c.Status(fiber.StatusOK).JSON(&fiber.Map{
		"status":  "Success",
		"message": "Teams retrieved successfully",
		"data":    teams,
	})
}

func (h *teamHandler) AnalyzeOne(c *fiber.Ctx) error {
	teamId := c.Params("teamId")

	pythonURL := os.Getenv("PYTHON_API_URL")
	if pythonURL == "" {
		pythonURL = "http://localhost:8001"
	}

	body, _ := json.Marshal(map[string]string{"team_id": teamId})
	resp, err := http.Post(pythonURL+"/analyze-team", "application/json", bytes.NewBuffer(body))
	if err != nil {
		return c.Status(fiber.StatusBadGateway).JSON(&fiber.Map{
			"status":  "Failure",
			"message": "Analysis service unavailable",
		})
	}
	defer resp.Body.Close()

	result, err := io.ReadAll(resp.Body)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(&fiber.Map{
			"status":  "Failure",
			"message": "Failed to read analysis response",
		})
	}

	c.Set("Content-Type", "application/json")
	return c.Status(resp.StatusCode).Send(result)
}

func NewTeamHandler(router fiber.Router, repository models.TeamRepository) {
	handler := &teamHandler{
		repository: repository,
	}

	router.Get("/", handler.GetMany)
	router.Get("/device/:deviceUuid", handler.GetManyByDeviceUuid)
	router.Get("/:teamId", handler.GetOne)
	router.Post("/", handler.CreateOne)
	router.Post("/analyze/:teamId", handler.AnalyzeOne)
	router.Delete("/:teamId", handler.DeleteOne)
	router.Put("/:teamId", handler.UpdateOne)
}
