package models

import (
	"context"
	"time"

	"go.mongodb.org/mongo-driver/bson/primitive"
)

type Player struct {
	Name     string `json:"name" bson:"name"`
	Position string `json:"position" bson:"position"`
	NFL_Team string `json:"nfl_team" bson:"nfl_team"`
}

type Team struct {
	ID          primitive.ObjectID `json:"id" bson:"_id,omitempty"`
	TeamName    string             `json:"team_name" bson:"team_name"`
	DefenseType string             `json:"defense_type" bson:"defense_type"`
	Players     []Player           `json:"players" bson:"players"`
	CreatedAt   time.Time          `json:"created_at" bson:"created_at"`
}

type TeamRepository interface {
	GetMany(ctx context.Context) ([]*Team, error)
	GetOne(ctx context.Context, teamId uint) (*Team, error)
	CreateOne(ctx context.Context, team Team) (*Team, error)
	UpdateOne(ctx context.Context, teamId uint, team Team) (*Team, error)
	DeleteOne(ctx context.Context, teamId uint) error
}
