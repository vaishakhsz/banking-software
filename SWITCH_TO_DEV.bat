@echo off
echo Switching local environment to DEV Sandbox (ep-shiny-snow)...
git checkout dev
(
echo # PostgreSQL Database Connection ^(DEV Sandbox Branch^)
echo DATABASE_URL=postgresql://neondb_owner:npg_WBjT5wU1lrzy@ep-shiny-snow-azpqiece-pooler.c-3.ap-southeast-1.aws.neon.tech/neondb?sslmode=require^&channel_binding=require
) > .env
(
echo DATABASE_URL = "postgresql://neondb_owner:npg_WBjT5wU1lrzy@ep-shiny-snow-azpqiece-pooler.c-3.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
) > .streamlit\secrets.toml
echo Done! You are now in DEV mode. Any testing will use the safe Sandbox database.
pause
