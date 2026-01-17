package main

import (
	"log"
	"os"

	"github.com/gofiber/fiber/v2"
	"github.com/joho/godotenv"
	"github.com/sat-malla/nfl-random-team-analysis/backend/database"
	"github.com/sat-malla/nfl-random-team-analysis/backend/handlers"
	"github.com/sat-malla/nfl-random-team-analysis/backend/repositories"
)

func main() {
	err := godotenv.Load()
	if err != nil {
		log.Println("Error loading .env file")
	}

	mongoURI := os.Getenv("MONGO_URI")

	client := database.ConnectToDatabase(mongoURI)
	db := client.Database("nfl-random-teams") // chooses the database we want to use
	app := fiber.New(fiber.Config{
		AppName:      "NFL Random Team Analysis",
		ServerHeader: "Fiber",
	})

	// repositories
	eventRepo := repositories.NewEventRepository(db.Collection("events")) // creates repo with "events" collection to work with
	teamRepo := repositories.NewTeamRepository(db.Collection("teams"))    // creates repo with "teams" collection to work with

	// routing
	server := app.Group("/api")

	// handlers
	handlers.NewEventHandler(server.Group("/event"), eventRepo) // connects HTTP routes /api/event to handler, which uses repo
	handlers.NewTeamHandler(server.Group("/team"), teamRepo)    // connects HTTP routes /api/team to handler, which uses repo
	handlers.NewNFLPlayerHandler(server.Group("/players"), db.Collection("nfl_players"))

	log.Fatal(app.Listen(":8000"))
}
