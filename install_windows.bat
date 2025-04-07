@echo on
cd /d %~dp0
cd %

::copy .env.example
echo Check status .env file
if not exist .env (
    copy .env.example .env
    echo created .env file.
) else (
    echo file .env already exist.
)

echo Installing python libraries
pip install -r requirements.txt

PAUSE