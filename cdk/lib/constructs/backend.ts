/**
 * ECS Fargate Backend Construct for Error QA application
 * Creates a containerized FastAPI backend with load balancing and auto-scaling
 */

import { Construct } from "constructs";
import * as ecs from "aws-cdk-lib/aws-ecs";
import * as elbv2 from "aws-cdk-lib/aws-elasticloadbalancingv2";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import * as ecr from "aws-cdk-lib/aws-ecr";
import * as logs from "aws-cdk-lib/aws-logs";
import * as rds from "aws-cdk-lib/aws-rds";
import * as iam from "aws-cdk-lib/aws-iam";
import { Duration, RemovalPolicy } from "aws-cdk-lib";
import { EnvironmentConfig } from "../config";

export interface BackendConstructProps {
  config: EnvironmentConfig;
  vpc: ec2.Vpc;
  database: rds.DatabaseInstance;
  databaseSecret: any; // secrets.Secret
  cacheEndpoint: string;
  cachePort: string;
}

export class BackendConstruct extends Construct {
  public readonly cluster: ecs.Cluster;
  public readonly service: ecs.FargateService;
  public readonly loadBalancer: elbv2.ApplicationLoadBalancer;
  public readonly targetGroup: elbv2.ApplicationTargetGroup;
  public readonly repository: ecr.Repository;
  public readonly taskRole: iam.Role;
  public readonly executionRole: iam.Role;

  constructor(scope: Construct, id: string, props: BackendConstructProps) {
    super(scope, id);

    const { config, vpc, database, databaseSecret, cacheEndpoint, cachePort } =
      props;

    // Create ECR repository for backend Docker images
    this.repository = new ecr.Repository(this, "Repository", {
      repositoryName: `${config.environment}-errorqa-backend`,
      removalPolicy: RemovalPolicy.DESTROY,
      imageScanOnPush: true,
      encryptionKey: undefined,
    });

    // Create CloudWatch log group
    const logGroup = new logs.LogGroup(this, "LogGroup", {
      logGroupName: `/ecs/${config.environment}/errorqa-backend`,
      retention: logs.RetentionDays.ONE_WEEK,
      removalPolicy: RemovalPolicy.DESTROY,
    });

    // Create task execution role
    this.executionRole = new iam.Role(this, "ExecutionRole", {
      assumedBy: new iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
      description: "ECS task execution role for backend",
    });

    // Allow pulling from ECR
    this.executionRole.addManagedPolicy(
      iam.ManagedPolicy.fromAwsManagedPolicyName(
        "service-role/AmazonECSTaskExecutionRolePolicy"
      )
    );

    // Allow reading secrets
    this.executionRole.addToPrincipalPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ["secretsmanager:GetSecretValue"],
        resources: [databaseSecret.secretArn],
      })
    );

    // Allow logging to CloudWatch
    this.executionRole.addToPrincipalPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: [
          "logs:CreateLogStream",
          "logs:PutLogEvents",
        ],
        resources: [logGroup.logGroupArn],
      })
    );

    // Create task role for application permissions
    this.taskRole = new iam.Role(this, "TaskRole", {
      assumedBy: new iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
      description: "ECS task role for backend application",
    });

    // Allow writing to S3 for file uploads
    this.taskRole.addToPrincipalPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ["s3:PutObject", "s3:GetObject", "s3:DeleteObject"],
        resources: ["arn:aws:s3:::errorqa-*/*"],
      })
    );

    // Create ECS cluster
    this.cluster = new ecs.Cluster(this, "Cluster", {
      vpc,
      clusterName: `${config.environment}-errorqa-backend`,
    });

    // Create security group for backend
    const backendSecurityGroup = new ec2.SecurityGroup(this, "BackendSG", {
      vpc,
      description: "Security group for ECS backend",
      allowAllOutbound: true,
    });

    // Allow ALB to access backend
    backendSecurityGroup.addIngressRule(
      ec2.Peer.ipv4(config.vpc.cidr),
      ec2.Port.tcp(config.backend.containerPort),
      "Allow from ALB"
    );

    // Create task definition
    const taskDefinition = new ecs.FargateTaskDefinition(
      this,
      "TaskDefinition",
      {
        memoryLimitMiB: config.backend.memory,
        cpu: config.backend.cpu,
        executionRole: this.executionRole,
        taskRole: this.taskRole,
      }
    );

    // Get database credentials from secret
    const dbHost = database.dbInstanceEndpointAddress;
    const dbPort = database.dbInstanceEndpointPort;
    const dbName = database.databaseName || "errorqa";

    // Add container to task definition
    const container = taskDefinition.addContainer("Backend", {
      image: ecs.ContainerImage.fromRegistry(
        `${this.repository.repositoryUriForTag("latest")}`
      ),
      logging: ecs.LogDriver.awsLogs({
        streamPrefix: "ecs",
        logGroup,
      }),
      portMappings: [
        {
          containerPort: config.backend.containerPort,
          protocol: ecs.Protocol.TCP,
        },
      ],
      // Environment variables
      environment: {
        ENVIRONMENT: config.environment,
        DATABASE_HOST: dbHost,
        DATABASE_PORT: dbPort,
        DATABASE_NAME: dbName,
        DATABASE_USER: "postgres",
        REDIS_HOST: cacheEndpoint,
        REDIS_PORT: cachePort,
        REDIS_DB: "0",
        WORKERS: "4",
        LOG_LEVEL: config.environment === "prod" ? "INFO" : "DEBUG",
      },
      // Secrets from Secrets Manager
      secrets: {
        DATABASE_PASSWORD: ecs.Secret.fromSecretsManager(
          databaseSecret,
          "password"
        ),
      },
    });

    // Health check
    container.addHealthCheck({
      command: [
        "CMD-SHELL",
        `curl -f http://localhost:${config.backend.containerPort}${config.backend.healthCheckPath} || exit 1`,
      ],
      interval: Duration.seconds(30),
      timeout: Duration.seconds(5),
      retries: 3,
      startPeriod: Duration.seconds(60),
    });

    // Create Fargate service
    this.service = new ecs.FargateService(this, "Service", {
      cluster: this.cluster,
      taskDefinition,
      desiredCount: config.backend.desiredCount,
      vpcSubnets: {
        subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
      },
      securityGroups: [backendSecurityGroup],
      assignPublicIp: false,
      serviceName: `${config.environment}-errorqa-backend`,
    });

    // Create Application Load Balancer
    this.loadBalancer = new elbv2.ApplicationLoadBalancer(
      this,
      "LoadBalancer",
      {
        vpc,
        internetFacing: true,
        loadBalancerName: `${config.environment}-errorqa-alb`,
      }
    );

    // Create target group
    this.targetGroup = new elbv2.ApplicationTargetGroup(this, "TargetGroup", {
      vpc,
      port: config.backend.containerPort,
      protocol: elbv2.ApplicationProtocol.HTTP,
      targetType: elbv2.TargetType.IP,
      targetGroupName: `${config.environment}-errorqa-tg`,
      healthCheck: {
        path: config.backend.healthCheckPath,
        interval: Duration.seconds(30),
        timeout: Duration.seconds(5),
        healthyThresholdCount: 2,
        unhealthyThresholdCount: 3,
        matcher: elbv2.HealthCheck.greedyMatcher(),
      },
    });

    // Attach service to target group
    this.service.attachToApplicationTargetGroup(this.targetGroup);

    // Add listener to load balancer
    this.loadBalancer.addListener("HttpListener", {
      port: 80,
      protocol: elbv2.ApplicationProtocol.HTTP,
      defaultTargetGroups: [this.targetGroup],
    });

    // Configure auto-scaling if enabled
    if (config.backend.enableAutoScaling) {
      const scaling = this.service.autoScaleTaskCount({
        minCapacity: config.backend.minCapacity,
        maxCapacity: config.backend.maxCapacity,
      });

      scaling.scaleOnCpuUtilization("CpuScaling", {
        targetUtilizationPercent: 70,
      });

      scaling.scaleOnMemoryUtilization("MemoryScaling", {
        targetUtilizationPercent: 80,
      });
    }

    // Outputs
    new (require("aws-cdk-lib").CfnOutput)(this, "LoadBalancerDNS", {
      value: this.loadBalancer.loadBalancerDnsName,
      description: "Load balancer DNS name",
      exportName: `${config.environment}-alb-dns`,
    });

    new (require("aws-cdk-lib").CfnOutput)(this, "LoadBalancerUrl", {
      value: `http://${this.loadBalancer.loadBalancerDnsName}`,
      description: "Backend API URL",
      exportName: `${config.environment}-api-url`,
    });

    new (require("aws-cdk-lib").CfnOutput)(this, "RepositoryUri", {
      value: this.repository.repositoryUri,
      description: "ECR repository URI",
      exportName: `${config.environment}-ecr-repo-uri`,
    });

    new (require("aws-cdk-lib").CfnOutput)(this, "EcsClusterName", {
      value: this.cluster.clusterName,
      description: "ECS cluster name",
      exportName: `${config.environment}-ecs-cluster`,
    });

    new (require("aws-cdk-lib").CfnOutput)(this, "EcsServiceName", {
      value: this.service.serviceName,
      description: "ECS service name",
      exportName: `${config.environment}-ecs-service`,
    });
  }
}
