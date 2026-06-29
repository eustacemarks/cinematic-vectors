variable "environment" {}
variable "vpc_id" {}
variable "private_subnet_ids" {}
variable "alb_target_group_arn" {}
variable "task_role_arn" {}
variable "execution_role_arn" {}
variable "ecr_urls" {}
variable "secrets_arn" {}
variable "rds_endpoint" {}

resource "aws_ecs_cluster" "main" {
  name = "${var.environment}-movie-search"
}

resource "aws_security_group" "tasks" {
  name   = "${var.environment}-tasks"
  vpc_id = var.vpc_id

  ingress {
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_ecs_task_definition" "api" {
  family                   = "${var.environment}-api"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 512
  memory                   = 1024
  task_role_arn            = var.task_role_arn
  execution_role_arn       = var.execution_role_arn

  container_definitions = jsonencode([{
    name  = "api"
    image = "${var.ecr_urls["api"]}:latest"
    portMappings = [{ containerPort = 8080 }]
    secrets = [
      { name = "JWT_SECRET",        valueFrom = "${var.secrets_arn}:JWT_SECRET::" },
      { name = "POSTGRES_PASSWORD", valueFrom = "${var.secrets_arn}:POSTGRES_PASSWORD::" },
    ]
    environment = [
      { name = "MCP_SERVER_URL",  value = "http://mcp-server:8000" },
      { name = "ASPNETCORE_URLS", value = "http://+:8080" },
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = "/ecs/${var.environment}/api"
        "awslogs-region"        = "us-east-1"
        "awslogs-stream-prefix" = "api"
      }
    }
  }])
}

resource "aws_ecs_task_definition" "mcp" {
  family                   = "${var.environment}-mcp"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 512
  memory                   = 1024
  task_role_arn            = var.task_role_arn
  execution_role_arn       = var.execution_role_arn

  container_definitions = jsonencode([{
    name  = "mcp-server"
    image = "${var.ecr_urls["mcp-server"]}:latest"
    portMappings = [{ containerPort = 8000 }]
    secrets = [
      { name = "POSTGRES_PASSWORD", valueFrom = "${var.secrets_arn}:POSTGRES_PASSWORD::" },
    ]
    environment = [
      { name = "POSTGRES_USER", value = "movieuser" },
      { name = "POSTGRES_DB",   value = "moviedb" },
      { name = "POSTGRES_HOST", value = var.rds_endpoint },
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = "/ecs/${var.environment}/mcp"
        "awslogs-region"        = "us-east-1"
        "awslogs-stream-prefix" = "mcp"
      }
    }
  }])
}

resource "aws_ecs_service" "api" {
  name            = "${var.environment}-api"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = var.private_subnet_ids
    security_groups = [aws_security_group.tasks.id]
  }

  load_balancer {
    target_group_arn = var.alb_target_group_arn
    container_name   = "api"
    container_port   = 8080
  }
}

resource "aws_ecs_service" "mcp" {
  name            = "${var.environment}-mcp"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.mcp.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = var.private_subnet_ids
    security_groups = [aws_security_group.tasks.id]
  }
}

# Autoscaling for API
resource "aws_appautoscaling_target" "api" {
  max_capacity       = 4
  min_capacity       = 1
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.api.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "api_cpu" {
  name               = "${var.environment}-api-cpu"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.api.resource_id
  scalable_dimension = aws_appautoscaling_target.api.scalable_dimension
  service_namespace  = aws_appautoscaling_target.api.service_namespace

  target_tracking_scaling_policy_configuration {
    target_value = 70.0
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
  }
}
