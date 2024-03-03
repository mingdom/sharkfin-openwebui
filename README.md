# Sharkin + Open WebUI

This is a fork from https://github.com/open-webui/open-webui

```
git clone git@github.com:mingdom/sharkfin-openwebui.git
cd open-webui/

# Copying required .env file
cp -RPp .env.example .env

# Building Frontend Using Node
npm i
npm run build

# Serving Frontend with the Backend
cd ./backend
pip install -r requirements.txt
bash start.sh
```