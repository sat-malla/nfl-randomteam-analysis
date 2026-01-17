package repositories

import (
	"context"
	"math/rand"

	"github.com/sat-malla/nfl-random-team-analysis/backend/models"
	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/mongo"
)

type NFLPlayerRepository struct {
	collection *mongo.Collection
}

func (r *NFLPlayerRepository) GetAllPlayers(ctx context.Context) ([]*models.NFLPlayer, error) {
	cursor, err := r.collection.Find(ctx, bson.M{})
	if err != nil {
		return nil, err
	}
	defer cursor.Close(ctx)

	var players []*models.NFLPlayer
	if err := cursor.All(ctx, &players); err != nil {
		return nil, err
	}

	return players, nil
}

func (r *NFLPlayerRepository) GetByPosition(ctx context.Context, position string) ([]*models.NFLPlayer, error) {
	cursor, err := r.collection.Find(ctx, bson.M{"position": position})
	if err != nil {
		return nil, err
	}
	defer cursor.Close(ctx)

	var players []*models.NFLPlayer
	if err := cursor.All(ctx, &players); err != nil {
		return nil, err
	}

	return players, nil
}

func (r *NFLPlayerRepository) GetRandomByPosition(ctx context.Context, position string) (*models.NFLPlayer, error) {
	cursor, err := r.collection.Find(ctx, bson.M{"position": position})
	if err != nil {
		return nil, err
	}
	defer cursor.Close(ctx)

	var players []*models.NFLPlayer
	if err := cursor.All(ctx, &players); err != nil {
		return nil, err
	}

	return players[rand.Intn(len(players))], nil
}

func (r *NFLPlayerRepository) GetManyRandomByPosition(ctx context.Context, position string, count int) ([]*models.NFLPlayer, error) {
	cursor, err := r.collection.Find(ctx, bson.M{"position": position})
	if err != nil {
		return nil, err
	}
	defer cursor.Close(ctx)

	var players []*models.NFLPlayer
	if err := cursor.All(ctx, &players); err != nil {
		return nil, err
	}

	var res []*models.NFLPlayer
	for i := 0; i < count && i < len(players); i++ {
		res = append(res, players[rand.Intn(len(players))])
	}

	return res, nil
}

func (r *NFLPlayerRepository) GetOneFromManyPositions(ctx context.Context, positions []string) (*models.NFLPlayer, error) {
	cursor, err := r.collection.Find(ctx, bson.M{"position": bson.M{"$in": positions}})
	if err != nil {
		return nil, err
	}
	defer cursor.Close(ctx)

	var players []*models.NFLPlayer
	if err := cursor.All(ctx, &players); err != nil {
		return nil, err
	}

	return players[rand.Intn(len(players))], nil
}

func NewNFLPlayerRepository(collection *mongo.Collection) models.NFLPlayerRepository {
	return &NFLPlayerRepository{
		collection: collection,
	}
}
