# DigitalDMS
Digital Database Management System

## Version info

## I. Version info

-   Python: 3.9 
-   Library & Framework: See [requirements.txt](./requirement.txt) 


## II. Set up project
- Create a blank folder.
## Set up virtual environment
```
python3 -m venv venv
```

## Activate the virtual environment

```
source venv/bin/activate
```
For windows:
```
venv\Script\activate
```
## Clone the repository
```
git clone <repo_link>
```
## Install libraries
Make sure that virtual environment is activated:

```
cd DigitalDMS
pip install -r requirements.txt
```

## Run Docker for Postgres (Or if you already had postgres then config in .env file)
Make sure that you in the level of the docker-compose.yml

If you already had postgres, config host, user and password in .env file

If you dont, run the command below for docker postgres, make sure you have docker in your computer then get to .env and config DATABASE_HOST='your_ipv4' 
```
docker-compose up -d
```

## Make migrations
Get into the level of manage.py

Make sure that virtual environment is activated:

```
python3 manage.py makemigrations
python3 manage.py migrate
```
## Run development server

Make sure that virtual environment is activated:

```
python3 manage.py runserver
```

## Create superuser
```
python3 manage.py createsuperuser
```

## Admin Page
http://127.0.0.1:8000/admin
## API Page
http://127.0.0.1:8000/api/docs