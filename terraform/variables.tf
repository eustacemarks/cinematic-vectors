variable "aws_region" {
  default = "us-east-1"
}

variable "environment" {
  description = "dev or prod"
}

variable "vpc_cidr" {
  default = "10.0.0.0/16"
}

variable "postgres_password" {
  sensitive = true
}

variable "jwt_secret" {
  sensitive = true
}
