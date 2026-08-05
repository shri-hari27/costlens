package main

import (
	"context"
	"encoding/json"
	"io"
	"log"
	"net/http"
	"os"
	"time"

	"github.com/Azure/azure-sdk-for-go/sdk/azidentity"
	"github.com/Azure/azure-sdk-for-go/sdk/storage/azblob"
	"github.com/gorilla/mux"
)

var (
	blobClient    *azblob.Client
	storageAcct   string
	containerName = "cost-snapshots"
	wasteContainer = "waste-reports"
)

func initBlobClient() error {
	storageAcct = os.Getenv("STORAGE_ACCOUNT_NAME")
	if storageAcct == "" {
		log.Fatal("STORAGE_ACCOUNT_NAME environment variable not set")
	}

	clientID := os.Getenv("AZURE_CLIENT_ID")
	var cred *azidentity.WorkloadIdentityCredential
	var err error

	if clientID != "" {
		cred, err = azidentity.NewWorkloadIdentityCredential(&azidentity.WorkloadIdentityCredentialOptions{
			ClientID: clientID,
		})
	} else {
		cred, err = azidentity.NewWorkloadIdentityCredential(nil)
	}
	if err != nil {
		return err
	}

	serviceURL := "https://" + storageAcct + ".blob.core.windows.net/"
	blobClient, err = azblob.NewClient(serviceURL, cred, nil)
	return err
}

func downloadBlob(ctx context.Context, container, blobName string) ([]byte, error) {
	resp, err := blobClient.DownloadStream(ctx, container, blobName, nil)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	return io.ReadAll(resp.Body)
}

func healthzHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
}

func summaryHandler(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := context.WithTimeout(r.Context(), 10*time.Second)
	defer cancel()

	data, err := downloadBlob(ctx, containerName, "latest.json")
	if err != nil {
		http.Error(w, `{"error":"failed to read latest.json"}`, http.StatusInternalServerError)
		log.Println("summaryHandler error:", err)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.Write(data)
}

func trendHandler(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := context.WithTimeout(r.Context(), 15*time.Second)
	defer cancel()

	pager := blobClient.NewListBlobsFlatPager(containerName, nil)
	var blobNames []string
	for pager.More() {
		page, err := pager.NextPage(ctx)
		if err != nil {
			http.Error(w, `{"error":"failed to list snapshots"}`, http.StatusInternalServerError)
			log.Println("trendHandler list error:", err)
			return
		}
		for _, blob := range page.Segment.BlobItems {
			if *blob.Name != "latest.json" {
				blobNames = append(blobNames, *blob.Name)
			}
		}
	}

	// Keep last 14 (blob names expected as dated JSON files, sorted lexically = chronologically)
	if len(blobNames) > 14 {
		blobNames = blobNames[len(blobNames)-14:]
	}

	var trend []json.RawMessage
	for _, name := range blobNames {
		data, err := downloadBlob(ctx, containerName, name)
		if err != nil {
			continue
		}
		trend = append(trend, json.RawMessage(data))
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(trend)
}

func wasteHandler(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := context.WithTimeout(r.Context(), 10*time.Second)
	defer cancel()

	data, err := downloadBlob(ctx, wasteContainer, "latest.json")
	if err != nil {
		http.Error(w, `{"error":"failed to read waste report"}`, http.StatusInternalServerError)
		log.Println("wasteHandler error:", err)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.Write(data)
}

func main() {
	if err := initBlobClient(); err != nil {
		log.Fatalf("failed to initialize blob client: %v", err)
	}

	r := mux.NewRouter()
	r.HandleFunc("/healthz", healthzHandler).Methods("GET")
	r.HandleFunc("/api/summary", summaryHandler).Methods("GET")
	r.HandleFunc("/api/trend", trendHandler).Methods("GET")
	r.HandleFunc("/api/waste", wasteHandler).Methods("GET")

	// Serve static frontend files
	r.PathPrefix("/").Handler(http.FileServer(http.Dir("./static")))

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	log.Printf("CostLens backend listening on :%s", port)
	if err := http.ListenAndServe(":"+port, r); err != nil {
		log.Fatal(err)
	}
}
