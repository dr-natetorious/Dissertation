# Deployment Automation for Dissertation Data Collector

## How do I initialize my environment

```sh
virtualenv .env
.env/scripts/activate.ps1
pip3 install -r requirements.txt
```

## How do I launch the deployer

```sh
docker-deploy/debug.bat
```

## How do I deploy everything

```sh
cdk deploy Infrastructure -a /files/app.py --require-approval never

cdk deploy DataCollection -a /files/app.py --require-approval never
```
