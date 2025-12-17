terraform {
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = ">= 2.0.0"
    }
  }
}

provider "docker" {}

# ---------------------------
# Network
# ---------------------------
resource "docker_network" "micro_net" {
  name   = "micro_net"
  driver = "bridge"
}

# ---------------------------
# Volumes
# ---------------------------
resource "docker_volume" "dbdata" {
  name = "dbdata"
}

resource "docker_volume" "redisdata" {
  name = "redisdata"
}

# ---------------------------
# PostgreSQL
# ---------------------------
resource "docker_container" "postgres_users" {
  name    = "postgres_users"
  image   = "postgres:15"
  restart = "unless-stopped"

  env = [
    "POSTGRES_USER=user",
    "POSTGRES_PASSWORD=password",
    "POSTGRES_DB=usersdb"
  ]

  volumes {
    volume_name    = docker_volume.dbdata.name
    container_path = "/var/lib/postgresql/data"
  }

  volumes {
    host_path      = abspath("${path.module}/init.sql")
    container_path = "/docker-entrypoint-initdb.d/init.sql"
    read_only      = true
  }

  networks_advanced {
    name    = docker_network.micro_net.name
    aliases = ["db"]
  }

  ports {
    internal = 5432
    external = 5432
  }
}

# ---------------------------
# Redis
# ---------------------------
resource "docker_container" "redis" {
  name    = "redis_cache"
  image   = "redis:latest"
  restart = "unless-stopped"

  volumes {
    volume_name    = docker_volume.redisdata.name
    container_path = "/data"
  }

  networks_advanced {
    name    = docker_network.micro_net.name
    aliases = ["redis"]
  }

  ports {
    internal = 6379
    external = 6379
  }
}

# ---------------------------
# Users Service Image
# ---------------------------
resource "docker_image" "users_service_img" {
  name = "users-service-img"

  build {
    context    = "${path.module}/users-service"
    dockerfile = "Dockerfile"
  }
}

# ---------------------------
# Users Service Container
# ---------------------------
resource "docker_container" "users_service" {
  name    = "users-service"
  image   = docker_image.users_service_img.image_id
  restart = "unless-stopped"

  networks_advanced {
    name    = docker_network.micro_net.name
    aliases = ["users-service"]
  }

  depends_on = [
    docker_container.postgres_users,
    docker_container.redis
  ]

  ports {
    internal = 3000
    external = 3000
  }
}

# ---------------------------
# Products Service Image
# ---------------------------
resource "docker_image" "products_service_img" {
  name = "products-service-img"

  build {
    context    = "${path.module}/products-service"
    dockerfile = "Dockerfile"
  }
}

# ---------------------------
# Products Service Container
# ---------------------------
resource "docker_container" "products_service" {
  name    = "products-service"
  image   = docker_image.products_service_img.image_id
  restart = "unless-stopped"

  networks_advanced {
    name    = docker_network.micro_net.name
    aliases = ["products-service"]
  }

  depends_on = [
    docker_container.postgres_users,
    docker_container.redis
  ]

  ports {
    internal = 4000
    external = 4000
  }
}
