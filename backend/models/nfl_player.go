package models

import (
	"context"

	"go.mongodb.org/mongo-driver/bson/primitive"
)

type NFLPlayer struct {
	ID              primitive.ObjectID `json:"id" bson:"_id,omitempty"`
	PlayerID        string             `json:"player_id" bson:"player_id"`
	FullName        string             `json:"full_name" bson:"full_name"`
	FirstName       string             `json:"first_name" bson:"first_name"`
	LastName        string             `json:"last_name" bson:"last_name"`
	Position        string             `json:"position" bson:"position"`
	NFLTeam         string             `json:"team" bson:"team"`
	DepthChartOrder int                `json:"depth_chart_order" bson:"depth_chart_order"`
}

type NFLPlayerRepository interface {
	GetAllPlayers(ctx context.Context) ([]*NFLPlayer, error)
	GetByPosition(ctx context.Context, position string) ([]*NFLPlayer, error)
	GetRandomByPosition(ctx context.Context, position string) (*NFLPlayer, error)
	GetManyRandomByPosition(ctx context.Context, position string, count int) ([]*NFLPlayer, error)
	GetOneFromManyPositions(ctx context.Context, positions []string) (*NFLPlayer, error)
}
