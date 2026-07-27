package repositories

import (
	"context"

	"github.com/sat-malla/nfl-random-team-analysis/backend/models"
	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/bson/primitive"
	"go.mongodb.org/mongo-driver/mongo"
)

type TeamRepository struct {
	collection *mongo.Collection
}

func (r *TeamRepository) GetMany(ctx context.Context) ([]*models.Team, error) {
	cursor, err := r.collection.Find(ctx, bson.M{})
	if err != nil {
		return nil, err
	}
	defer cursor.Close(ctx)

	var teams []*models.Team
	if err := cursor.All(ctx, &teams); err != nil {
		return nil, err
	}

	return teams, nil
}

func (r *TeamRepository) GetOne(ctx context.Context, teamId string) (*models.Team, error) {
	oid, err := primitive.ObjectIDFromHex(teamId)
	if err != nil {
		return nil, err
	}

	teamResult := r.collection.FindOne(ctx, bson.M{"_id": oid})

	if teamResult.Err() != nil {
		return nil, teamResult.Err()
	}

	var team models.Team
	if err := teamResult.Decode(&team); err != nil {
		return nil, err
	}

	return &team, nil
}

func (r *TeamRepository) CreateOne(ctx context.Context, team models.Team) (*models.Team, error) {
	team.ID = primitive.NewObjectID()

	_, err := r.collection.InsertOne(ctx, team)

	if err != nil {
		return nil, err
	}
	return &team, nil
}

func (r *TeamRepository) DeleteOne(ctx context.Context, teamId uint) error {
	_, err := r.collection.DeleteOne(ctx, bson.M{"_id": teamId})
	return err
}

func (r *TeamRepository) UpdateOne(ctx context.Context, teamId uint, team models.Team) (*models.Team, error) {
	var updatedTeam models.Team

	_, err := r.collection.UpdateOne(ctx, bson.M{"_id": teamId}, bson.M{"$set": team})

	if err != nil {
		return nil, err
	}

	teamResult := r.collection.FindOne(ctx, bson.M{"_id": teamId})

	if teamResult.Err() != nil {
		return nil, teamResult.Err()
	}

	if err := teamResult.Decode(&updatedTeam); err != nil {
		return nil, err
	}

	return &updatedTeam, nil
}

func (r *TeamRepository) GetManyByDeviceUuid(ctx context.Context, deviceUuid string) ([]*models.Team, error) {
	cursor, err := r.collection.Find(ctx, bson.M{"device_uuid": deviceUuid})
	if err != nil {
		return nil, err
	}
	defer cursor.Close(ctx)

	var teams []*models.Team
	if err := cursor.All(ctx, &teams); err != nil {
		return nil, err
	}

	return teams, nil
}

func NewTeamRepository(collection *mongo.Collection) models.TeamRepository {
	return &TeamRepository{
		collection: collection,
	}
}
