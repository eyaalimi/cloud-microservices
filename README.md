# Cloud Microservices Project

## 🚀 Overview

This project demonstrates a basic microservices architecture using:
- **Terraform** (with Docker provider) to provision the infrastructure
- **PostgreSQL** database
- **Redis** cache
- Two Python microservices: `users-service` and `products-service`
- (Optional) Nginx Gateway, Prometheus, etc.

---

## 🗂️ Project Structure

```
.
├── main.tf                 # Main Terraform config for Docker infrastructure
├── init.sql                # SQL initialization for PostgreSQL
├── users-service/
│   ├── Dockerfile
│   ├── main.py
│   ├── requirements.txt
│   └── .env                # (NOT tracked, see .gitignore)
├── products-service/
│   ├── Dockerfile
│   ├── main.py
│   ├── requirements.txt
│   └── .env                # (optional, not tracked)
├── .gitignore
├── README.md
└── ...
```

---

## 🔧 Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop) **running**
- [Terraform](https://www.terraform.io/downloads.html) v1.x+
- Python 3.x (for local dev/service modification)
- A [GitHub Personal Access Token](https://github.com/settings/tokens) if using private repositories

---

## ⚡ Quickstart

### 1. **Clone the repository**

```bash
git clone https://github.com/YOURUSERNAME/cloud-microservices.git
cd cloud-microservices
```

### 2. **Copy/Create .env files**

Create a `users-service/.env` file (NEVER commit it):

```
DATABASE_URL=postgresql://user:password@db:5432/usersdb
REDIS_URL=redis://redis:6379/0
FLASK_ENV=development
# Add others as needed
```

If `products-service` needs a `.env`, repeat there.

### 3. **Provision the stack with Terraform**

```bash
terraform init
terraform apply
```
After approval, this will:
- Build and run the PostgreSQL and Redis containers (with persistent volumes)
- Build and run the `users-service` and `products-service` images/containers
- Set up an isolated Docker bridge network

### 4. **Accessing the services**

- **users-service:** http://localhost:3000/
- **products-service:** http://localhost:4000/
- **PostgreSQL:** localhost:5432 (`user/password`)
- **Redis:** localhost:6379

---

## 📄 Environment variables

**DO NOT COMMIT your `.env` files!**
They are ignored by `.gitignore` and must be created locally for credentials/secrets.

---

## 🛠️ Useful Commands

```bash
# Rebuild and restart everything
terraform apply

# Stop and remove all managed containers
terraform destroy

# See running Docker containers
docker ps

# Connect to the PostgreSQL container (example)
docker exec -it postgres_users psql -U user -d usersdb
```

---

## 📝 Notes

- Don’t push `.terraform/`, `*.tfstate`, or any `.env` file.
- Add/modify microservices as needed; update Terraform accordingly.
- For any issues during init/apply, check that Docker Desktop is running, and that volumes/containers aren't conflicting (`docker ps -a` / `docker rm ...`).

---

## 📣 Author

Eya Alimi  
[GitHub](https://github.com/eyaalimi)

---
