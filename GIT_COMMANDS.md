# Git-команды для первой публикации

git init
git branch -M main
git add .
git commit -m "Релиз v3.4.0"
git remote add origin https://github.com/bezuglyy/off_light.git
git push -u origin main

# Создание тега релиза
git tag -a v3.4.0 -m "Релиз v3.4.0"
git push origin v3.4.0
