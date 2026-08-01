package database

import (
	"context"
	"log"
	"time"

	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
)

func ConnectToDatabase(uri string) *mongo.Client {
	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()

	serverAPI := options.ServerAPI(options.ServerAPIVersion1)
	opts := options.Client().ApplyURI(uri).SetServerAPIOptions(serverAPI).SetConnectTimeout(3 * time.Second).SetServerSelectionTimeout(3 * time.Second)

	client, err := mongo.Connect(ctx, opts)
	if err != nil {
		log.Printf("Warning: MongoDB connection failed: %v — MongoDB-dependent routes will be unavailable", err)
		return nil
	}

	if err = client.Ping(ctx, nil); err != nil {
		log.Printf("Warning: MongoDB ping failed: %v — MongoDB-dependent routes will be unavailable", err)
		return nil
	}

	log.Println("Connected to MongoDB")
	return client
}

func GetCollection(client *mongo.Client, dbName string, collectionName string) *mongo.Collection {
	return client.Database(dbName).Collection(collectionName)
}
