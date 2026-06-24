/**
 * ElastiCache Redis Construct for Error QA application
 * Creates a Redis cluster for caching and session storage
 */

import { Construct } from "constructs";
import * as elasticache from "aws-cdk-lib/aws-elasticache";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import { EnvironmentConfig } from "../config";

export interface CacheConstructProps {
  config: EnvironmentConfig;
  vpc: ec2.Vpc;
}

export class CacheConstruct extends Construct {
  public readonly cacheSubnetGroup: elasticache.CfnSubnetGroup;
  public readonly securityGroup: ec2.SecurityGroup;
  public readonly cluster: elasticache.CfnReplicationGroup;

  constructor(scope: Construct, id: string, props: CacheConstructProps) {
    super(scope, id);

    const { config, vpc } = props;

    // Create security group for cache
    this.securityGroup = new ec2.SecurityGroup(this, "CacheSG", {
      vpc,
      description: "Security group for Redis cache",
      allowAllOutbound: true,
    });

    // Allow inbound traffic on port 6379 (Redis)
    this.securityGroup.addIngressRule(
      ec2.Peer.ipv4(config.vpc.cidr),
      ec2.Port.tcp(6379),
      "Allow Redis from VPC"
    );

    // Get private subnets for cache subnet group
    const privateSubnets = vpc.privateSubnets;
    const subnetIds = privateSubnets.map((subnet) => subnet.subnetId);

    // Create cache subnet group
    this.cacheSubnetGroup = new elasticache.CfnSubnetGroup(
      this,
      "CacheSubnetGroup",
      {
        subnetIds,
        description: "Subnet group for Redis cluster",
      }
    );

    // Create parameter group with custom settings
    const parameterGroup = new elasticache.CfnParameterGroup(
      this,
      "CacheParameterGroup",
      {
        family: "redis7",
        description: "Custom parameter group for Error QA Redis",
        properties: {
          // Enable encryption in transit
          "tls-auth-clients": "optional",
          // Disable dangerous commands
          "timeout": "300",
          "tcp-backlog": "511",
          // Connection pooling settings
          "maxclients": "65000",
        },
      }
    );

    // Create Redis replication group (cluster)
    this.cluster = new elasticache.CfnReplicationGroup(
      this,
      "CacheCluster",
      {
        replicationGroupDescription: "Redis cluster for Error QA application",
        engine: "redis",
        engineVersion: config.cache.engineVersion,
        cacheNodeType: config.cache.nodeType,
        numCacheClusters: config.cache.numCacheNodes,
        automaticFailoverEnabled: config.cache.autoFailoverEnabled,
        cacheSubnetGroupName: this.cacheSubnetGroup.ref,
        vpcSecurityGroupIds: [this.securityGroup.securityGroupId],
        parameterGroupName: parameterGroup.ref,
        // Encryption settings
        atRestEncryptionEnabled: config.cache.enableEncryption,
        transitEncryptionEnabled: config.cache.enableEncryption,
        transitEncryptionMode: "preferred",
        authToken: config.environment === "prod" ? this.generateAuthToken() : undefined,
        // Backup and maintenance
        snapshotRetentionLimit: config.environment === "prod" ? 7 : 1,
        snapshotWindow: "03:00-05:00", // UTC
        preferredMaintenanceWindow: "mon:05:00-mon:07:00",
        // Logging
        logDeliveryConfigurations: [
          {
            destinationDetails: {
              cloudWatchLogsDetails: {
                logGroup: `/aws/elasticache/${config.environment}/redis-slow-log`,
              },
            },
            destinationType: "cloudwatch-logs",
            enabled: config.environment !== "dev",
            logFormat: "json",
            logType: "slow-log",
          },
          {
            destinationDetails: {
              cloudWatchLogsDetails: {
                logGroup: `/aws/elasticache/${config.environment}/redis-engine-log`,
              },
            },
            destinationType: "cloudwatch-logs",
            enabled: config.environment !== "dev",
            logFormat: "json",
            logType: "engine-log",
          },
        ],
        tags: [
          { key: "Name", value: `${config.environment}-redis-cluster` },
          { key: "Environment", value: config.environment },
        ],
      }
    );

    // Outputs
    new (require("aws-cdk-lib").CfnOutput)(this, "CacheEndpoint", {
      value: this.cluster.attrPrimaryEndPointAddress,
      description: "Redis primary endpoint",
      exportName: `${config.environment}-cache-endpoint`,
    });

    new (require("aws-cdk-lib").CfnOutput)(this, "CachePort", {
      value: "6379",
      description: "Redis port",
      exportName: `${config.environment}-cache-port`,
    });

    new (require("aws-cdk-lib").CfnOutput)(this, "CacheConnectionString", {
      value: config.cache.enableEncryption
        ? `rediss://${this.cluster.attrPrimaryEndPointAddress}:6379`
        : `redis://${this.cluster.attrPrimaryEndPointAddress}:6379`,
      description: "Redis connection string",
      exportName: `${config.environment}-cache-connection-string`,
    });
  }

  /**
   * Generate a secure auth token for Redis
   * In production, this should be stored in Secrets Manager
   */
  private generateAuthToken(): string {
    const length = 32;
    const chars =
      "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*";
    let token = "";
    for (let i = 0; i < length; i++) {
      token += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return token;
  }

  /**
   * Get the cache endpoint for connection strings
   */
  getConnectionString(): string {
    return `redis://${this.cluster.attrPrimaryEndPointAddress}:6379`;
  }
}
