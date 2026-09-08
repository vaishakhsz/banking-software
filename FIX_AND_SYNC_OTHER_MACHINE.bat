@echo off
echo ========================================================
echo FIXING MERGE CONFLICTS AND SYNCING LATEST CODE...
echo ========================================================
cd /d "C:\Users\vaish\OneDrive\Documents\GitHub\banking-software"

echo 1. Fetching latest branches from GitHub...
git fetch origin

echo 2. Switching to dev branch...
git checkout dev

echo 3. Resetting to clean GitHub version (removes any conflict markers)...
git reset --hard origin/dev

echo 4. Pulling latest updates...
git pull origin dev

echo ========================================================
echo SYNC COMPLETE! Your code is now 100%% clean and up to date.
echo ========================================================
pause
