/**
 * Main Error QA Stack
 * Orchestrates all infrastructure components for the Error QA application
 */

import { Stack, StackProps, Tags } from "aws-cdk-lib";
import { Construct } from "constructs";
import {
  VpcConstruct,
  DatabaseConstruct,
  CacheConstruct,
  BackendConstruct,
  FrontendConstruct,
} from "../constructs";
import { EnvironmentConfig } from "../config";

export interface ErrorQaStackProps extends StackProps {
  config: EnvironmentConfig;
}

export class ErrorQaStack extends Stack {
  public readonly vpcConstruct: VpcConstruct;
  public readonly databaseConstruct: DatabaseConstruct;
  public readonly cacheConstruct: CacheConstruct;
  public readonly backendConstruct: BackendConstruct;
  public readonly frontendConstruct: FrontendConstruct;

  constructor(scope: Construct, id: string, props: ErrorQaStackProps) {
    super(scope, id, props);

    const { config } = props;

    // Apply tags to entire stack
    Object.entries(config.tags).forEach(([key, value]) => {
      Tags.of(this).add(key, value);
    });

    // Create VPC
    this.vpcConstruct = new VpcConstruct(this, "Vpc", {
      config,
    });

    // Create Database
    this.databaseConstruct = new DatabaseConstruct(this, "Database", {
      config,
      vpc: this.vpcConstruct.vpc,
    });

    // Create Cache
    this.cacheConstruct = new CacheConstruct(this, "Cache", {
      config,
      vpc: this.vpcConstruct.vpc,
    });

    // Create Backend
    this.backendConstruct = new BackendConstruct(this, "Backend", {
      config,
      vpc: this.vpcConstruct.vpc,
      database: this.databaseConstruct.database,
      databaseSecret: this.databaseConstruct.secret,
      cacheEndpoint: this.cacheConstruct.cluster.attrPrimaryEndPointAddress,
      cachePort: "6379",
    });

    // Create Frontend
    this.frontendConstruct = new FrontendConstruct(this, "Frontend", {
      config,
      backendApiUrl: `http://${this.backendConstruct.loadBalancer.loadBalancerDnsName}`,
    });

    // Grant database access to backend security group
    this.databaseConstruct.securityGroup.addIngressRule(
      this.backendConstruct.service,
      require("aws-cdk-lib/aws-ec2").Port.tcp(5432),
      "Allow backend to access database"
    );

    // Grant cache access to backend security group
    this.cacheConstruct.securityGroup.addIngressRule(
      this.backendConstruct.service,
      require("aws-cdk-lib/aws-ec2").Port.tcp(6379),
      "Allow backend to access cache"
    );

    // Stack summary
    new (require("aws-cdk-lib").CfnOutput)(this, "StackName", {
      value: this.stackName,
      description: "Stack name",
    });

    new (require("aws-cdk-lib").CfnOutput)(this, "Environment", {
      value: config.environment,
      description: "Environment",
    });

    new (require("aws-cdk-lib").CfnOutput)(this, "Region", {
      value: this.region,
      description: "AWS region",
    });

    new (require("aws-cdk-lib").CfnOutput)(this, "SummaryUrl", {
      value: `https://console.aws.amazon.com/cloudformation/home?region=${this.region}#/stacks/detail?stackName=${this.stackName}`,
      description: "CloudFormation console link",
    });
  }
}
