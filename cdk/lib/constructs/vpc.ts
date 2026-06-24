/**
 * VPC Construct for Error QA application
 * Creates a VPC with public and private subnets across multiple AZs
 */

import { Construct } from "constructs";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import { EnvironmentConfig } from "../config";

export interface VpcConstructProps {
  config: EnvironmentConfig;
}

export class VpcConstruct extends Construct {
  public readonly vpc: ec2.Vpc;
  public readonly publicSubnets: ec2.ISubnet[];
  public readonly privateSubnets: ec2.ISubnet[];

  constructor(scope: Construct, id: string, props: VpcConstructProps) {
    super(scope, id);

    const { config } = props;

    // Create VPC with public and private subnets
    this.vpc = new ec2.Vpc(this, "Vpc", {
      cidr: config.vpc.cidr,
      maxAzs: config.vpc.maxAzs,
      natGateways: config.vpc.natGateways,
      subnetConfiguration: [
        {
          name: "Public",
          subnetType: ec2.SubnetType.PUBLIC,
          cidrMask: 24,
        },
        {
          name: "Private",
          subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
          cidrMask: 24,
        },
      ],
      enableDns: true,
    });

    // Add VPC Flow Logs for monitoring
    new ec2.FlowLog(this, "FlowLog", {
      resourceType: ec2.FlowLogResourceType.fromVpc(this.vpc),
      trafficType: ec2.FlowLogTrafficType.ALL,
      destination: ec2.FlowLogDestination.toCloudWatchLogs(
        undefined,
        {
          iam: true,
        }
      ),
    });

    this.publicSubnets = this.vpc.publicSubnets;
    this.privateSubnets = this.vpc.privateSubnets;

    // Output VPC info
    new (require("aws-cdk-lib").CfnOutput)(this, "VpcId", {
      value: this.vpc.vpcId,
      description: "VPC ID",
      exportName: `${config.environment}-vpc-id`,
    });

    new (require("aws-cdk-lib").CfnOutput)(this, "VpcCidr", {
      value: this.vpc.vpcCidr,
      description: "VPC CIDR Block",
      exportName: `${config.environment}-vpc-cidr`,
    });
  }

  /**
   * Get security group for database access (PostgreSQL)
   */
  getDatabaseSecurityGroup(): ec2.ISecurityGroup {
    return ec2.SecurityGroup.fromSecurityGroupId(
      this,
      "DbSecurityGroup",
      this.vpc.vpcId
    );
  }

  /**
   * Get security group for cache access (Redis)
   */
  getCacheSecurityGroup(): ec2.ISecurityGroup {
    return ec2.SecurityGroup.fromSecurityGroupId(
      this,
      "CacheSecurityGroup",
      this.vpc.vpcId
    );
  }
}
