
module "eks" {
  create_eks   = var.kubernetes
  source       = "terraform-aws-modules/eks/aws"
  cluster_name = "kubernetes_${var.key_name}"
  subnets      = var.vpc_private_subnets

  tags = {
    Environment = "training"
    GithubRepo  = "terraform-aws-eks"
    GithubOrg   = "terraform-aws-modules"
  }

  vpc_id = var.vpc_id

  worker_groups = [
    {
      name                          = "worker-group-1"
      instance_type                 = "t2.small"
      additional_userdata           = "echo foo bar"
      asg_desired_capacity          = 1
      additional_security_group_ids = [var.sg_worker_group_mgmt_one_id]
    },
    {
      name                          = "worker-group-2"
      instance_type                 = "t2.medium"
      additional_userdata           = "echo foo bar"
      additional_security_group_ids = [var.sg_worker_group_mgmt_two_id]
      asg_desired_capacity          = 1
    },
  ]


}

data "aws_eks_cluster" "cluster" {
  count = var.kubernetes ? 1 : 0
  name = module.eks.cluster_id
}

data "aws_eks_cluster_auth" "cluster" {
  count = var.kubernetes ? 1 : 0
  name = module.eks.cluster_id
}

provider "kubernetes" {
  load_config_file       = "false"
  host                   = data.aws_eks_cluster.cluster[0].endpoint
  token                  = data.aws_eks_cluster_auth.cluster[0].token
  cluster_ca_certificate = base64decode(data.aws_eks_cluster.cluster[0].certificate_authority.0.data)
}
