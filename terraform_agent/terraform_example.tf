terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.16"
    }
  }
  required_version = ">= 1.2.0"
}

variable "name" {
  description = "Your Name"
  type        = string
}
variable "email" {
  description = "Your email"
  type        = string
}
variable "ip" {
  description = "Your public IP address for SSH access"
  type        = string
}
variable "profile" {
  description = "Your EC2 profile credential name"
  type        = string
}
variable "region" {
  description = "AWS region"
  type        = string
}

variable "nameonly" {
  description = "Name without alphanumeric characters, hyphen, periods and underscores"
  type        = string
}

variable "ec2user" {
  description = "EC2-user"
  type        = string
}

provider "aws" {
  region = var.region
  #shared_credentials_file = "~/.aws/credentials"
  profile = var.profile
}

data "aws_ami" "specific_ami" {
  owners = ["amazon"]

  filter {
    name   = "image-id"
    values = ["ami-053a45fff0a704a47"]
  }
}

resource "tls_private_key" "key_pair" {
  algorithm = "RSA"
  rsa_bits  = 2048
}

resource "aws_key_pair" "generated_key" {
  key_name   = "${var.name}1"
  public_key = tls_private_key.key_pair.public_key_openssh
}

resource "local_file" "private_key" {
  content  = tls_private_key.key_pair.private_key_pem
  filename = "${path.module}/${var.name}.pem"

  file_permission = "0600"
}

data "aws_vpc" "default" {
  default = true
}

data "aws_subnet" "default" {
  filter {
    name   = "availability-zone"
    values = ["${var.region}a"]
  }
  vpc_id = data.aws_vpc.default.id
}

data "aws_security_group" "default" {
  vpc_id = data.aws_vpc.default.id

  filter {
    name   = "group-name"
    values = ["default"]
  }
}

# Create a security group for EC2 instance with SSH access from your IP
/* resource "aws_security_group" "ec2_sg" {
  name        = "ec2-sg"
  description = "Security group for EC2 instance by ${var.name}"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["${var.ip}/32"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "security_group_${var.name}"
    tm   = var.name
  }
} */

resource "aws_security_group_rule" "ssh_rule" {
  type              = "ingress"
  from_port         = "22"
  to_port           = "22"
  protocol          = "tcp"
  cidr_blocks       = ["${var.ip}/32"]
  security_group_id = data.aws_security_group.default.id
}

# Creaate VPC endpoints for S3 y ECR
/* resource "aws_vpc_endpoint" "s3" {
  vpc_id       = data.aws_vpc.default.id
  service_name = "com.amazonaws.${var.region}.s3"

  tags = {
    Name = "S3 VPC Endpoint"
    tm   = var.name
  }
}

resource "aws_vpc_endpoint" "ecr" {
  vpc_id       = data.aws_vpc.default.id
  service_name = "com.amazonaws.${var.region}.ecr.dkr"

  tags = {
    Name = "ECR VPC Endpoint"
    tm   = var.name
  }
} */

# Obtain el S3 bucket is exist
/* data "aws_s3_bucket" "existing_bucket" {
  bucket = "tm-terraform-bucket"
} */

# Create S3 bucket
resource "aws_s3_bucket" "my_bucket" {
  bucket = "tm-terraform-bucket-${var.nameonly}"
  acl    = "private"

  /*  lifecycle_rule {
    id      = "keep_versions_forever"
    enabled = true
    expiration {
      days = 0
    }
  }
  lifecycle {
    prevent_destroy = true
  } */

  tags = {
    Name = "S3Bucket${var.name}"
    tm   = var.name
  }
}

# Obtain ECR if exists
/* data "aws_ecr_repository" "existing_repository" {
  name = "tm-terraform-repo"
} */

# Create ECR repository
resource "aws_ecr_repository" "my_repository" {
  name = "tm-terraform-repo-${var.nameonly}"
  tags = {
    Name = "Terraform ECR Repository"
    tm   = var.name
  }
}

# Obtain IAM role if exists
/* data "aws_iam_role" "existing_role" {
  name = "ec2-instance-role"
} */

# Create IAM role for EC2 instance with policies to access S3 and ECR
/* resource "aws_iam_role" "ec2_instance_role" {
  name = "ec2-instance-role"

  assume_role_policy = jsonencode({
    Statement = [
      {
        Effect = "Allow",
        Action = ["sts:AssumeRole"],
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ],
    Version = "2012-10-17"
  })

  tags = {
    Name = "EC2 Instance Role"
    tm   = var.name
  }
} */

# IAM policies for restricted access to S3 and ECR
/* resource "aws_iam_policy" "s3_ecr_access" {
  name = "s3-ecr-access"
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = ["s3:Get*", "s3:List*", "s3:PutObject", "s3:DeleteObject"],
        Resource = ["${aws_s3_bucket.my_bucket.arn}", "${aws_s3_bucket.my_bucket.arn}/*"]
      },
      {
        Effect   = "Allow",
        Action   = ["ecr:GetAuthorizationToken", "ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"],
        Resource = "*"
      },
      {
        Effect   = "Allow",
        Action   = ["ecr:GetRepositoryPolicy", "ecr:ListImages", "ecr:DescribeRepositories"],
        Resource = ["${aws_ecr_repository.my_repository.arn}"]
      }
    ]
  })

  tags = {
    Name = "S3 and ERC, AIM  Policies"
    tm   = var.name
  }
} */

# Attach policies
/* resource "aws_iam_role_policy_attachment" "attach_s3_ecr_policy" {
  role       = aws_iam_role.ec2_instance_role.name
  policy_arn = aws_iam_policy.s3_ecr_access.arn
} */

# Create instance's profile with IAM Role
/* resource "aws_iam_instance_profile" "ec2_profile" {
  name = "ec2-instance-profile"
  role = aws_iam_role.ec2_instance_role.name

  tags = {
    Name = "EC2 Instance Profile"
    tm   = var.name
  }
} */

output "instance_public_ip" {
  value = aws_instance.ec2_resource.public_ip

}

# Create EC2 instance with custom security group and IAM role
resource "aws_instance" "ec2_resource" {
  ami                    = data.aws_ami.specific_ami.id # Updated AMI for newer instances
  instance_type          = "t3.micro"
  key_name               = aws_key_pair.generated_key.key_name
  subnet_id              = data.aws_subnet.default.id
  vpc_security_group_ids = [data.aws_security_group.default.id /* , aws_security_group.ec2_sg.id */] # default was related to default security group: data.aws_security_group.default.id

  root_block_device {
    volume_size           = 10
    volume_type           = "gp3"
    delete_on_termination = true
  }

  /* iam_instance_profile {
    name = aws_iam_role.ec2_instance_role.name
  } */

  #iam_instance_profile = aws_iam_instance_profile.ec2_profile.name

  tags = {
    Name = "ec2_terraform_full_test_${var.nameonly}"
    tm   = var.name
  }

  provisioner "remote-exec" {
    inline = [
      "sudo mkdir -p /home/ec2-user/.ssh",
      "echo '${tls_private_key.key_pair.public_key_openssh}' | sudo tee /home/ec2-user/.ssh/authorized_keys",
      "sudo chmod 700 /home/ec2-user/.ssh",
      "sudo chmod 600 /home/ec2-user/.ssh/authorized_keys",
      "sudo chown -R ec2-user:ec2-user /home/ec2-user/.ssh"
    ]

    connection {
      type        = "ssh"
      user        = var.ec2user
      private_key = tls_private_key.key_pair.private_key_pem
      host        = self.public_ip
    }
  }

  provisioner "file" {
    source      = "./cleanup.sh"
    destination = "/tmp/cleanup.sh" # Copiar a /tmp primero

    connection {
      type        = "ssh"
      user        = var.ec2user
      private_key = tls_private_key.key_pair.private_key_pem
      host        = self.public_ip
    }
  }

  provisioner "remote-exec" {
    inline = [
      "sudo mv /tmp/cleanup.sh /home/ec2-user/cleanup.sh",
      "sudo chmod +x /home/ec2-user/cleanup.sh"
    ]

    connection {
      type        = "ssh"
      user        = var.ec2user
      private_key = tls_private_key.key_pair.private_key_pem
      host        = self.public_ip
    }
  }

  depends_on = [
    data.aws_vpc.default,
    data.aws_subnet.default /* ,
    aws_iam_instance_profile.ec2_profile */
  ]
}

# Bootstrap script contents (cleanup.sh)