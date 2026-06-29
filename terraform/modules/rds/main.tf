variable "environment" {}
variable "subnet_ids" {}
variable "vpc_id" {}
variable "postgres_password" { sensitive = true }

resource "aws_db_subnet_group" "main" {
  name       = "${var.environment}-movie-search"
  subnet_ids = var.subnet_ids
}

resource "aws_security_group" "rds" {
  name   = "${var.environment}-rds"
  vpc_id = var.vpc_id

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }
}

resource "aws_db_instance" "main" {
  identifier             = "${var.environment}-movie-search"
  engine                 = "postgres"
  engine_version         = "16"
  instance_class         = "db.t3.medium"
  allocated_storage      = 20
  db_name                = "moviedb"
  username               = "movieuser"
  password               = var.postgres_password
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  skip_final_snapshot    = true
  storage_encrypted      = true

  # pgvector is installed via the pipeline on first run
}

output "endpoint" { value = aws_db_instance.main.endpoint }
