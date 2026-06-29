variable "environment" {}
variable "postgres_password" { sensitive = true }
variable "jwt_secret"        { sensitive = true }

resource "aws_secretsmanager_secret" "app" {
  name = "movie-search/${var.environment}/app"
}

resource "aws_secretsmanager_secret_version" "app" {
  secret_id = aws_secretsmanager_secret.app.id
  secret_string = jsonencode({
    POSTGRES_PASSWORD = var.postgres_password
    JWT_SECRET        = var.jwt_secret
  })
}

output "secrets_arn" { value = aws_secretsmanager_secret.app.arn }
