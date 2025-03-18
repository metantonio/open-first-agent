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

resource "aws_security_group_rule" "ssh_rule" {
  type              = "ingress"
  from_port         = "22"
  to_port           = "22"
  protocol          = "tcp"
  cidr_blocks       = ["${var.ip}/32"]
  security_group_id = data.aws_security_group.default.id
}

# Create S3 bucket
resource "aws_s3_bucket" "my_bucket" {
  bucket = "tm-terraform-bucket-${var.nameonly}"
  acl    = "private"

  tags = {
    Name = "S3Bucket${var.name}"
    tm   = var.name
  }
}

# Create ECR repository
resource "aws_ecr_repository" "my_repository" {
  name = "tm-terraform-repo-${var.nameonly}"
  tags = {
    Name = "Terraform ECR Repository"
    tm   = var.name
  }
}

output "instance_public_ip" {
  value = aws_instance.ec2_resource.public_ip

}

# Create EC2 instance with custom security group and IAM role
resource "aws_instance" "ec2_resource" {
  ami                    = data.aws_ami.specific_ami.id 
  instance_type          = "t3.micro"
  key_name               = aws_key_pair.generated_key.key_name
  subnet_id              = data.aws_subnet.default.id
  vpc_security_group_ids = [data.aws_security_group.default.id]

  root_block_device {
    volume_size           = 10
    volume_type           = "gp3"
    delete_on_termination = true
  }

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
    destination = "/tmp/cleanup.sh"

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
    data.aws_subnet.default
  ]
}