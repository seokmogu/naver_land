#!/bin/bash

# Cloud Run 배포 스크립트
set -e

PROJECT_ID="gbd-match"
REGION="asia-northeast3"  # 서울 리전
SERVICE_NAME="naver-collector"

echo "🚀 Cloud Run 배포 시작"
echo "========================"

# 1. Cloud Build API 활성화
echo "📋 필요한 API 활성화 중..."
gcloud services enable cloudbuild.googleapis.com --project=$PROJECT_ID
gcloud services enable run.googleapis.com --project=$PROJECT_ID
gcloud services enable containerregistry.googleapis.com --project=$PROJECT_ID

# 2. Cloud Build 실행
echo "🔨 Docker 이미지 빌드 및 배포 중..."
gcloud builds submit --config cloudbuild.yaml --project=$PROJECT_ID

# 3. Cloud Scheduler 설정
echo "⏰ Cloud Scheduler 설정 중..."
gcloud services enable cloudscheduler.googleapis.com --project=$PROJECT_ID

# 서비스 URL 가져오기
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --project=$PROJECT_ID --format='value(status.url)')

# Cloud Scheduler Job 생성 (매일 오전 4시 실행 - 한국시간 기준)
gcloud scheduler jobs create http naver-collection-daily \
    --location=$REGION \
    --schedule="0 4 * * *" \
    --time-zone="Asia/Seoul" \
    --uri="${SERVICE_URL}" \
    --http-method=GET \
    --oidc-service-account-email="${PROJECT_ID}@appspot.gserviceaccount.com" \
    --project=$PROJECT_ID \
    || echo "⚠️ 스케줄러가 이미 존재합니다"

echo "✅ 배포 완료!"
echo "========================"
echo "🔗 서비스 URL: $SERVICE_URL"
echo "⏰ 스케줄: 매일 오전 4시 (한국시간)"
echo ""
echo "📊 수동 실행:"
echo "gcloud scheduler jobs run naver-collection-daily --location=$REGION --project=$PROJECT_ID"
echo ""
echo "📈 로그 확인:"
echo "gcloud logging read \"resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME\" --limit 50 --project=$PROJECT_ID"