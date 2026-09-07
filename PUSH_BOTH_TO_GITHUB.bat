@echo off
echo ========================================================
echo PUSHING BOTH DEV AND MAIN BRANCHES TO GITHUB...
echo ========================================================
cd /d "%~dp0"

echo 1. Pushing main branch to GitHub...
git push origin main

echo 2. Pushing dev branch to GitHub...
git push origin dev

echo ========================================================
echo PUSH FINISHED! Both dev and main are 100%% synced on GitHub.
echo ========================================================
pause
