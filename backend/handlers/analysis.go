package handlers

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"time"

	"github.com/gofiber/fiber/v2"
	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/bson/primitive"
	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
)

type analysisHandler struct {
	collection *mongo.Collection
}

type SaveAnalysisRequest struct {
	TeamID   string         `json:"team_id"`
	Analysis map[string]any `json:"analysis"`
}

func (h *analysisHandler) GetAnalysis(c *fiber.Ctx) error {
	teamId := c.Params("teamId")
	objId, err := primitive.ObjectIDFromHex(teamId)
	if err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(&fiber.Map{
			"status":  "Failure",
			"message": "Invalid team ID",
		})
	}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	var result bson.M
	err = h.collection.FindOne(ctx, bson.M{"team_id": objId}).Decode(&result)
	if err == mongo.ErrNoDocuments {
		return c.Status(fiber.StatusNotFound).JSON(&fiber.Map{
			"status":  "NotFound",
			"message": "No analysis found for this team",
		})
	}
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(&fiber.Map{
			"status":  "Failure",
			"message": "Failed to fetch analysis",
		})
	}

	return c.Status(fiber.StatusOK).JSON(&fiber.Map{
		"status": "Success",
		"data":   result["analysis"],
	})
}

func (h *analysisHandler) SaveAnalysis(c *fiber.Ctx) error {
	teamId := c.Params("teamId")
	objId, err := primitive.ObjectIDFromHex(teamId)
	if err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(&fiber.Map{
			"status":  "Failure",
			"message": "Invalid team ID",
		})
	}

	var body SaveAnalysisRequest
	if err := c.BodyParser(&body); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(&fiber.Map{
			"status":  "Failure",
			"message": "Invalid request body",
		})
	}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	doc := bson.M{
		"team_id":    objId,
		"analysis":   body.Analysis,
		"updated_at": time.Now(),
	}

	opts := options.Update().SetUpsert(true)
	_, err = h.collection.UpdateOne(ctx, bson.M{"team_id": objId}, bson.M{"$set": doc}, opts)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(&fiber.Map{
			"status":  "Failure",
			"message": "Failed to save analysis",
		})
	}

	return c.Status(fiber.StatusOK).JSON(&fiber.Map{
		"status":  "Success",
		"message": "Analysis saved",
	})
}

type SummarizeRequest struct {
	Message  string         `json:"message"`
	Analysis map[string]any `json:"analysis"`
}

type groqMessage struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

type groqRequest struct {
	Model    string        `json:"model"`
	Messages []groqMessage `json:"messages"`
}

type groqChoice struct {
	Message groqMessage `json:"message"`
}

type groqResponse struct {
	Choices []groqChoice `json:"choices"`
}

func (h *analysisHandler) SummarizeAnalysis(c *fiber.Ctx) error {
	var body SummarizeRequest
	if err := c.BodyParser(&body); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(&fiber.Map{
			"status":  "Failure",
			"message": "Invalid request body",
		})
	}

	apiKey := os.Getenv("GROQ_API_KEY")
	if apiKey == "" {
		return c.Status(fiber.StatusInternalServerError).JSON(&fiber.Map{
			"status":  "Failure",
			"message": "GROQ_API_KEY not configured",
		})
	}

	analysisJSON, err := json.Marshal(body.Analysis)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(&fiber.Map{
			"status":  "Failure",
			"message": "Failed to serialize analysis",
		})
	}

	systemPrompt := `You are an NFL analyst assistant. The user has built a custom NFL team using a fantasy-style random team generator, and you have access to that team's full season simulation results. 
	Your job is to give sharp, clear, opinionated analysis — like a sports analyst on TV, not a textbook. Be concise (3-5 sentences max per response unless asked for detail). Use the stats to back up your points. Refer to the team's projected wins, playoff/Super Bowl odds, scoring, and standout players by name.
	You are also a helpful assistant that can answer questions about the team and the NFL.`

	userContent := fmt.Sprintf("Here is the team's analysis data:\n%s\n\nUser message: %s", string(analysisJSON), body.Message)

	payload := groqRequest{
		Model: "openai/gpt-oss-120b",
		Messages: []groqMessage{
			{Role: "system", Content: systemPrompt},
			{Role: "user", Content: userContent},
		},
	}

	payloadBytes, err := json.Marshal(payload)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(&fiber.Map{
			"status":  "Failure",
			"message": "Failed to build Groq request",
		})
	}

	req, err := http.NewRequest("POST", "https://api.groq.com/openai/v1/chat/completions", bytes.NewReader(payloadBytes))
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(&fiber.Map{
			"status":  "Failure",
			"message": "Failed to create request",
		})
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+apiKey)

	client := &http.Client{Timeout: 30 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return c.Status(fiber.StatusBadGateway).JSON(&fiber.Map{
			"status":  "Failure",
			"message": "Failed to reach Groq API",
		})
	}
	defer resp.Body.Close()

	respBytes, err := io.ReadAll(resp.Body)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(&fiber.Map{
			"status":  "Failure",
			"message": "Failed to read Groq response",
		})
	}

	if resp.StatusCode != http.StatusOK {
		return c.Status(fiber.StatusBadGateway).JSON(&fiber.Map{
			"status":  "Failure",
			"message": fmt.Sprintf("Groq API error: %s", string(respBytes)),
		})
	}

	var groqResp groqResponse
	if err := json.Unmarshal(respBytes, &groqResp); err != nil || len(groqResp.Choices) == 0 {
		return c.Status(fiber.StatusInternalServerError).JSON(&fiber.Map{
			"status":  "Failure",
			"message": "Invalid response from Groq",
		})
	}

	return c.Status(fiber.StatusOK).JSON(&fiber.Map{
		"summary": groqResp.Choices[0].Message.Content,
	})
}

func NewAnalysisHandler(router fiber.Router, collection *mongo.Collection) {
	handler := &analysisHandler{collection: collection}
	router.Get("/:teamId", handler.GetAnalysis)
	router.Post("/summarize/:teamId", handler.SummarizeAnalysis)
	router.Post("/:teamId", handler.SaveAnalysis)
}
