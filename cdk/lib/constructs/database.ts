/**
 * RDS PostgreSQL Database Construct for Error QA application
 * Creates a multi-AZ PostgreSQL database with automated backups and encryption
 */

import { Construct } from "constructs";
import * as rds from "aws-cdk-lib/aws-rds";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import * as secretsmanager from "aws-cdk-lib/aws-secretsmanager";
import { Duration, RemovalPolicy, SecretValue } from "aws-cdk-lib";
import { EnvironmentConfig } from "../config";

export interface DatabaseConstructProps {
  config: EnvironmentConfig;
  vpc: ec2.Vpc;
}

export class DatabaseConstruct extends Construct {
  public readonly database: rds.DatabaseInstance;
  public readonly secret: secretsmanager.Secret;
  public readonly securityGroup: ec2.SecurityGroup;

  constructor(scope: Construct, id: string, props: DatabaseConstructProps) {
    super(scope, id);

    const { config, vpc } = props;

    // Create security group for database
    this.securityGroup = new ec2.SecurityGroup(this, "DatabaseSG", {
      vpc,
      description: "Security group for PostgreSQL database",
      allowAllOutbound: true,
    });

    // Allow inbound traffic on port 5432 (PostgreSQL)
    this.securityGroup.addIngressRule(
      ec2.Peer.ipv4(config.vpc.cidr),
      ec2.Port.tcp(5432),
      "Allow PostgreSQL from VPC"
    );

    // Create database secret for credentials
    this.secret = new secretsmanager.Secret(this, "DatabaseSecret", {
      generateSecretString: {
        secretStringTemplate: JSON.stringify({
          username: "postgres",
        }),
        generateStringKey: "password",
        passwordLength: 32,
        excludeCharacters: '"@/\\',
      },
      description: "PostgreSQL database credentials",
      removalPolicy: RemovalPolicy.RETAIN,
    });

    // Create database parameter group
    const parameterGroup = new rds.ParameterGroup(this, "ParameterGroup", {
      engine: rds.DatabaseEngine.postgres({
        version: rds.PostgresEngineVersion.VER_14_10,
      }),
      description: "Custom parameter group for Error QA database",
      parameters: {
        // Performance tuning for typical workload
        shared_buffers: "256000", // ~2GB for t3.micro/small
        max_connections: "100",
        work_mem: "1310", // ~10MB per operation
        maintenance_work_mem: "16000", // ~125MB for maintenance
        log_statement: config.environment === "prod" ? "mod" : "all",
        log_min_duration_statement: "1000", // Log queries > 1 second
        log_checkpoints: "1",
        log_connections: "1",
        log_disconnections: "1",
        log_lock_waits: "1",
        deadlock_timeout: "1000",
        // SSL configuration
        ssl: "1",
        ssl_cert_file: "/etc/ssl/certs/server.crt",
        ssl_key_file: "/etc/ssl/private/server.key",
      },
    });

    // Create RDS instance
    this.database = new rds.DatabaseInstance(this, "Instance", {
      engine: rds.DatabaseInstanceEngine.postgres({
        version: rds.PostgresEngineVersion.VER_14_10,
      }),
      instanceType: ec2.InstanceType.of(
        ec2.InstanceClass.T3,
        ec2.InstanceSize.MICRO
      ),
      vpc,
      vpcSubnets: {
        subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
      },
      allocatedStorage: config.database.allocatedStorage,
      maxAllocatedStorage: config.database.maxAllocatedStorage,
      storageType: rds.StorageType.GP3,
      storageEncrypted: config.database.enableEncryption,
      deletionProtection: config.environment === "prod",
      multiAz: config.database.multiAz,
      backupRetention: Duration.days(config.database.backupRetentionDays),
      preferredBackupWindow: "03:00-04:00", // UTC
      preferredMaintenanceWindow: "mon:04:00-mon:05:00",
      enableIamAuthentication: true,
      enableCloudwatchLogsExports: [
        "postgresql",
      ],
      securityGroups: [this.securityGroup],
      databaseName: "errorqa",
      credentials: rds.Credentials.fromSecret(this.secret),
      parameterGroup,
      enablePerformanceInsights: config.environment !== "dev",
      performanceInsightRetention: Duration.days(
        config.environment === "prod" ? 31 : 7
      ),
      removalPolicy:
        config.environment === "prod" ? RemovalPolicy.RETAIN : RemovalPolicy.DESTROY,
      monitoringInterval: config.database.enableEnhancedMonitoring
        ? Duration.minutes(1)
        : undefined,
    });

    // Outputs
    new (require("aws-cdk-lib").CfnOutput)(this, "DatabaseEndpoint", {
      value: this.database.dbInstanceEndpointAddress,
      description: "Database endpoint",
      exportName: `${config.environment}-db-endpoint`,
    });

    new (require("aws-cdk-lib").CfnOutput)(this, "DatabasePort", {
      value: this.database.dbInstanceEndpointPort,
      description: "Database port",
      exportName: `${config.environment}-db-port`,
    });

    new (require("aws-cdk-lib").CfnOutput)(this, "DatabaseName", {
      value: this.database.databaseName || "errorqa",
      description: "Database name",
      exportName: `${config.environment}-db-name`,
    });

    new (require("aws-cdk-lib").CfnOutput)(this, "DatabaseSecretArn", {
      value: this.secret.secretArn,
      description: "Database credentials secret ARN",
      exportName: `${config.environment}-db-secret-arn`,
    });
  }

  /**
   * Get the database endpoint for connection strings
   */
  getConnectionString(): string {
    return `postgresql://user:password@${this.database.dbInstanceEndpointAddress}:${this.database.dbInstanceEndpointPort}/errorqa`;
  }
}
