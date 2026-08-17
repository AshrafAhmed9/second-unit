#!/usr/bin/env bash
# Day 0. Run once, after: (1) a GCP project exists on the free trial with the
# hackathon's $100 credit applied, (2) `gcloud auth login` has been done.
# Costs nothing beyond API enablement — no resources are created here.
set -euo pipefail

: "${PROJECT_ID:?set PROJECT_ID=your-gcp-project-id}"

gcloud config set project "$PROJECT_ID"

gcloud services enable \
  run.googleapis.com \
  aiplatform.googleapis.com \
  secretmanager.googleapis.com \
  storage.googleapis.com \
  firestore.googleapis.com \
  artifactregistry.googleapis.com

gcloud firestore databases create --location=us-central1 --type=firestore-native || true

echo "Project setup complete for $PROJECT_ID. Next: infra/01_secrets.sh"
