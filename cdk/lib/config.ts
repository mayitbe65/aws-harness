/**
 * Configuration for Error QA CDK deployment
 * Supports dev, staging, and production environments
 */

export interface EnvironmentConfig {
  environment: string;
  region: string;
  vpc: {
    cidr: string;
    maxAzs: number;
    natGateways: number;
  };
  database: {
    engine: string;
    engineVersion: string;
    instanceType: string;
    allocatedStorage: number;
    maxAllocatedStorage: number;
    multiAz: boolean;
    backupRetentionDays: number;
    enableEncryption: boolean;
    enableEnhancedMonitoring: boolean;
  };
  cache: {
    engine: string;
    engineVersion: string;
    nodeType: string;
    numCacheNodes: number;
    autoFailoverEnabled: boolean;
    enableEncryption: boolean;
  };
  backend: {
    desiredCount: number;
    minCapacity: number;
    maxCapacity: number;
    cpu: number;
    memory: number;
    containerPort: number;
    healthCheckPath: string;
    enableAutoScaling: boolean;
    enableLoadBalancer: boolean;
  };
  frontend: {
    enableCloudFront: boolean;
    cacheTtlSeconds: number;
    enableCompression: boolean;
    enableHttps: boolean;
  };
  tags: {
    [key: string]: string;
  };
}

const commonTags = {
  Application: "ErrorQA",
  ManagedBy: "CDK",
  CreatedAt: new Date().toISOString(),
};

const devConfig: EnvironmentConfig = {
  environment: "dev",
  region: "us-east-1",
  vpc: {
    cidr: "10.0.0.0/16",
    maxAzs: 2,
    natGateways: 1, // Cost optimization: single NAT gateway
  },
  database: {
    engine: "postgres",
    engineVersion: "14.10",
    instanceType: "db.t3.micro", // Free tier eligible
    allocatedStorage: 20,
    maxAllocatedStorage: 100,
    multiAz: false, // Cost optimization
    backupRetentionDays: 7,
    enableEncryption: true,
    enableEnhancedMonitoring: false,
  },
  cache: {
    engine: "redis",
    engineVersion: "7.0",
    nodeType: "cache.t3.micro", // Free tier eligible
    numCacheNodes: 1,
    autoFailoverEnabled: false,
    enableEncryption: true,
  },
  backend: {
    desiredCount: 1,
    minCapacity: 1,
    maxCapacity: 2,
    cpu: 256,
    memory: 512,
    containerPort: 8000,
    healthCheckPath: "/health",
    enableAutoScaling: false, // Cost optimization for dev
    enableLoadBalancer: true,
  },
  frontend: {
    enableCloudFront: false, // Cost optimization: use S3 directly
    cacheTtlSeconds: 3600,
    enableCompression: true,
    enableHttps: false, // Use HTTP for dev
  },
  tags: {
    ...commonTags,
    Environment: "dev",
    CostCenter: "engineering",
  },
};

const stagingConfig: EnvironmentConfig = {
  environment: "staging",
  region: "us-east-1",
  vpc: {
    cidr: "10.1.0.0/16",
    maxAzs: 2,
    natGateways: 1,
  },
  database: {
    engine: "postgres",
    engineVersion: "14.10",
    instanceType: "db.t3.small",
    allocatedStorage: 50,
    maxAllocatedStorage: 500,
    multiAz: false,
    backupRetentionDays: 7,
    enableEncryption: true,
    enableEnhancedMonitoring: true,
  },
  cache: {
    engine: "redis",
    engineVersion: "7.0",
    nodeType: "cache.t3.small",
    numCacheNodes: 1,
    autoFailoverEnabled: false,
    enableEncryption: true,
  },
  backend: {
    desiredCount: 2,
    minCapacity: 2,
    maxCapacity: 4,
    cpu: 512,
    memory: 1024,
    containerPort: 8000,
    healthCheckPath: "/health",
    enableAutoScaling: true,
    enableLoadBalancer: true,
  },
  frontend: {
    enableCloudFront: true,
    cacheTtlSeconds: 3600,
    enableCompression: true,
    enableHttps: true,
  },
  tags: {
    ...commonTags,
    Environment: "staging",
    CostCenter: "operations",
  },
};

const prodConfig: EnvironmentConfig = {
  environment: "prod",
  region: "us-east-1",
  vpc: {
    cidr: "10.2.0.0/16",
    maxAzs: 2,
    natGateways: 2, // High availability
  },
  database: {
    engine: "postgres",
    engineVersion: "14.10",
    instanceType: "db.t3.medium",
    allocatedStorage: 100,
    maxAllocatedStorage: 1000,
    multiAz: true, // High availability
    backupRetentionDays: 30,
    enableEncryption: true,
    enableEnhancedMonitoring: true,
  },
  cache: {
    engine: "redis",
    engineVersion: "7.0",
    nodeType: "cache.t3.medium",
    numCacheNodes: 2, // Multi-node for failover
    autoFailoverEnabled: true,
    enableEncryption: true,
  },
  backend: {
    desiredCount: 3,
    minCapacity: 3,
    maxCapacity: 10,
    cpu: 512,
    memory: 1024,
    containerPort: 8000,
    healthCheckPath: "/health",
    enableAutoScaling: true,
    enableLoadBalancer: true,
  },
  frontend: {
    enableCloudFront: true,
    cacheTtlSeconds: 86400, // 24 hours
    enableCompression: true,
    enableHttps: true,
  },
  tags: {
    ...commonTags,
    Environment: "prod",
    CostCenter: "operations",
  },
};

export const getConfig = (environment: string = "dev"): EnvironmentConfig => {
  switch (environment.toLowerCase()) {
    case "staging":
      return stagingConfig;
    case "prod":
    case "production":
      return prodConfig;
    case "dev":
    case "development":
    default:
      return devConfig;
  }
};

export const allConfigs = {
  dev: devConfig,
  staging: stagingConfig,
  prod: prodConfig,
};
