resource "aws_instance" "app" {
  ami                         = data.aws_ami.ubuntu.id
  instance_type               = var.ec2_instance_type
  subnet_id                   = aws_subnet.public.id
  associate_public_ip_address = true
  key_name                    = var.key_pair_name
  iam_instance_profile        = aws_iam_instance_profile.ec2_profile.name
  vpc_security_group_ids      = [aws_security_group.app.id]

  root_block_device {
    volume_size = 30
    volume_type = "gp3"
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-app" })
}
