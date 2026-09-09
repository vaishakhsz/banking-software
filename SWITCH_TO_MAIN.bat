@echo off
echo Switching local environment to MAIN Production (ep-restless-haze)...
git checkout main
(
echo # PostgreSQL Database Connection ^(MAIN Production Branch^)
echo DATABASE_URL=postgresql://neondb_owner:npg_WBjT5wU1lrzy@ep-restless-haze-azsi5s6f-pooler.c-3.ap-southeast-1.aws.neon.tech/neondb?sslmode=require^&channel_binding=require
) > .env
(
echo DATABASE_URL = "postgresql://neondb_owner:npg_WBjT5wU1lrzy@ep-restless-haze-azsi5s6f-pooler.c-3.ap-southeast-1.aws.neon.tech/neondb?sslmode=require^&channel_binding=require"
) > .streamlit\secrets.toml
echo Done! You are now in MAIN mode connected to live production data.
pause
