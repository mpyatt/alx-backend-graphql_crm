# alx-backend-graphql_crm

A Django + GraphQL CRM backend for ALX Backend Engineering tasks.

## Features

- GraphQL endpoint powered by `graphene-django`
- Customer, Product, and Order models
- Example query: `{ hello }` → returns `"Hello, GraphQL!"`

## Getting Started

### Requirements

- Python 3.10+
- Django
- Graphene-Django
- django-filter

### Setup

```bash
git clone https://github.com/mpyatt/alx-backend-graphql_crm.git
cd alx-backend-graphql_crm
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
````

### Usage

Open [http://localhost:8000/graphql](http://localhost:8000/graphql) and run:

```graphql
{
  hello
}
```

### Project Structure

```md
alx-backend-graphql_crm/
├── alx_backend_graphql_crm/   # Project settings and schema
├── crm/                       # Main CRM app
├── manage.py
├── requirements.txt
├── .gitignore
└── README.md
```
