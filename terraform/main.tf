terraform {
  required_version = ">= 1.7"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  backend "s3" {
    bucket         = "movie-search-tfstate"
    key            = "terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "movie-search-tflock"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Project     = "movie-search"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

module "networking" {
  source      = "./modules/networking"
  environment = var.environment
  vpc_cidr    = var.vpc_cidr
}

module "ecr" {
  source      = "./modules/ecr"
  environment = var.environment
}

module "secrets" {
  source            = "./modules/secrets"
  environment       = var.environment
  postgres_password = var.postgres_password
  jwt_secret        = var.jwt_secret
}

module "iam" {
  source           = "./modules/iam"
  environment      = var.environment
  secrets_arn      = module.secrets.secrets_arn
}

module "rds" {
  source             = "./modules/rds"
  environment        = var.environment
  subnet_ids         = module.networking.private_subnet_ids
  vpc_id             = module.networking.vpc_id
  postgres_password  = var.postgres_password
}

module "alb" {
  source            = "./modules/alb"
  environment       = var.environment
  vpc_id            = module.networking.vpc_id
  public_subnet_ids = module.networking.public_subnet_ids
}

module "compute" {
  source              = "./modules/compute"
  environment         = var.environment
  vpc_id              = module.networking.vpc_id
  private_subnet_ids  = module.networking.private_subnet_ids
  alb_target_group_arn = module.alb.target_group_arn
  task_role_arn       = module.iam.task_role_arn
  execution_role_arn  = module.iam.execution_role_arn
  ecr_urls            = module.ecr.repository_urls
  secrets_arn         = module.secrets.secrets_arn
  rds_endpoint        = module.rds.endpoint
}
