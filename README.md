# VidReacher Labs – FullStack Free Tier Testing Build

## 🧩 Overview
This package contains everything to test VidReacher end-to-end on **Render**, **Vercel**, and **Supabase** – 100% free tier compatible.

### Components
- **FastAPI backend** with dummy AI + Analytics + Scheduler
- **React frontend** with Google Analytics (GA4) ready
- **Docker Compose** for local deployment
- **CI/CD GitHub workflow** for automated build testing
- **Brevo SMTP (Free)** for email notifications

## 🚀 Setup Steps
1. Unzip into a clean folder
2. Copy `.env.example` to `.env` and edit your credentials
3. Run locally with Docker:  
   ```bash
   docker compose up --build
   ```
4. Push to GitHub → Deploy backend on **Render** & frontend on **Vercel**
5. For persistent DB, use **Supabase Free PostgreSQL**
