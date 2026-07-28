package main

import (
	"context"
	"log"
	"os"

	"github.com/gofiber/fiber/v2"
	"github.com/joho/godotenv"
	"github.com/sat-malla/nfl-random-team-analysis/backend/database"
	"github.com/sat-malla/nfl-random-team-analysis/backend/handlers"
	"github.com/sat-malla/nfl-random-team-analysis/backend/repositories"
	"github.com/sat-malla/nfl-random-team-analysis/backend/services"
)

func main() {
	err := godotenv.Load()
	if err != nil {
		log.Println("Error loading .env file")
	}

	mongoURI := os.Getenv("MONGO_URI")

	client := database.ConnectToDatabase(mongoURI)

	app := fiber.New(fiber.Config{
		AppName: "NFL Random Team Analysis",
		ServerHeader: "Fiber",
	})

	// routing
	server := app.Group("/api")

	handlers.NewCoachHandler(server.Group("/coaches"))
	handlers.NewSimulateHandler(server.Group("/simulate"))
	handlers.NewOptimizeHandler(server.Group("/optimize"))
	handlers.NewDonateHandler(server.Group("/donate"))

	// MongoDB-dependent handlers — only registered when connected
	if client != nil {
		db := client.Database("nfl-random-teams")

		eventRepo := repositories.NewEventRepository(db.Collection("events"))
		teamRepo := repositories.NewTeamRepository(db.Collection("teams"))

		handlers.NewEventHandler(server.Group("/event"), eventRepo)
		handlers.NewTeamHandler(server.Group("/team"), teamRepo)
		handlers.NewNFLPlayerHandler(server.Group("/players"), db.Collection("nfl_players"))
		handlers.NewAnalysisHandler(server.Group("/analysis"), db.Collection("analyses"))

		sleeperService := services.NewSleeperService(db.Collection("nfl_players"))
		go func() {
			if err := sleeperService.SyncPlayers(context.Background()); err != nil {
				log.Printf("Failed to sync players: %v", err)
			}
		}()
	} else {
		log.Println("MongoDB unavailable — /event, /team, /players, /analysis routes disabled")
	}

	log.Fatal(app.Listen(":8000"))
}
