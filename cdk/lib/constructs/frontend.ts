/**
 * S3 + CloudFront Frontend Construct for Error QA application
 * Hosts React frontend static files with CDN distribution
 */

import { Construct } from "constructs";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as cloudfront from "aws-cdk-lib/aws-cloudfront";
import * as origins from "aws-cdk-lib/aws-cloudfront-origins";
import * as iam from "aws-cdk-lib/aws-iam";
import { Duration, RemovalPolicy } from "aws-cdk-lib";
import { EnvironmentConfig } from "../config";

export interface FrontendConstructProps {
  config: EnvironmentConfig;
  backendApiUrl: string;
}

export class FrontendConstruct extends Construct {
  public readonly bucket: s3.Bucket;
  public readonly distribution?: cloudfront.Distribution;
  public readonly bucketUrl: string;

  constructor(scope: Construct, id: string, props: FrontendConstructProps) {
    super(scope, id);

    const { config, backendApiUrl } = props;

    // Create S3 bucket for frontend
    this.bucket = new s3.Bucket(this, "Bucket", {
      bucketName: `${config.environment}-errorqa-frontend-${this.node.uniqueId.toLowerCase()}`,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
      versioned: config.environment === "prod",
      removalPolicy:
        config.environment === "prod" ? RemovalPolicy.RETAIN : RemovalPolicy.DESTROY,
      enforceSSL: true,
      publicReadAccess: false,
      serverAccessLogsPrefix: "logs/",
    });

    // Create Origin Access Identity for CloudFront
    const oai = new cloudfront.OriginAccessIdentity(this, "OAI", {
      comment: `OAI for ${config.environment} Error QA frontend`,
    });

    // Allow CloudFront to read from S3
    this.bucket.grantRead(oai);

    this.bucketUrl = this.bucket.bucketWebsiteUrl;

    // Create CloudFront distribution if enabled
    if (config.frontend.enableCloudFront) {
      const distribution = new cloudfront.Distribution(this, "Distribution", {
        defaultBehavior: {
          origin: new origins.S3Origin(this.bucket, {
            originAccessIdentity: oai,
          }),
          viewerProtocolPolicy:
            cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
          compress: config.frontend.enableCompression,
          cachePolicy: new cloudfront.CachePolicy(this, "CachePolicy", {
            comment: "Cache policy for React frontend",
            defaultTtl: Duration.seconds(config.frontend.cacheTtlSeconds),
            maxTtl: Duration.seconds(config.frontend.cacheTtlSeconds * 2),
            minTtl: Duration.seconds(0),
            enableAcceptEncodingGzip: config.frontend.enableCompression,
            enableAcceptEncodingBrotli: config.frontend.enableCompression,
            headerBehavior: cloudfront.CacheHeaderBehavior.none(),
            queryStringBehavior: cloudfront.CacheQueryStringBehavior.none(),
            cookieBehavior: cloudfront.CacheCookieBehavior.none(),
          }),
          allowedMethods: cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
          cachedMethods: cloudfront.CachedMethods.CACHE_GET_HEAD,
        },
        // Cache error pages
        errorResponses: [
          {
            httpStatus: 404,
            responseHttpStatus: 200,
            responsePagePath: "/index.html",
            ttl: Duration.seconds(300),
          },
          {
            httpStatus: 403,
            responseHttpStatus: 200,
            responsePagePath: "/index.html",
            ttl: Duration.seconds(300),
          },
        ],
        defaultRootObject: "index.html",
        comment: `${config.environment} Error QA frontend`,
        enabled: true,
        httpVersion: cloudfront.HttpVersion.HTTP2_AND_3,
        minimumProtocolVersion:
          cloudfront.SecurityPolicyProtocol.TLS_V1_2_2021_06,
        priceClass: cloudfront.PriceClass.PRICE_CLASS_100,
      });

      this.distribution = distribution;

      // Outputs for CloudFront
      new (require("aws-cdk-lib").CfnOutput)(this, "DistributionDomain", {
        value: distribution.distributionDomainName,
        description: "CloudFront distribution domain",
        exportName: `${config.environment}-frontend-domain`,
      });

      new (require("aws-cdk-lib").CfnOutput)(this, "DistributionUrl", {
        value: `https://${distribution.distributionDomainName}`,
        description: "Frontend URL",
        exportName: `${config.environment}-frontend-url`,
      });

      new (require("aws-cdk-lib").CfnOutput)(this, "DistributionId", {
        value: distribution.distributionId,
        description: "CloudFront distribution ID",
        exportName: `${config.environment}-cloudfront-id`,
      });
    }

    // Outputs
    new (require("aws-cdk-lib").CfnOutput)(this, "BucketName", {
      value: this.bucket.bucketName,
      description: "S3 bucket name for frontend",
      exportName: `${config.environment}-frontend-bucket`,
    });

    new (require("aws-cdk-lib").CfnOutput)(this, "BucketArn", {
      value: this.bucket.bucketArn,
      description: "S3 bucket ARN",
      exportName: `${config.environment}-frontend-bucket-arn`,
    });
  }

  /**
   * Get the S3 bucket for deployment
   */
  getFrontendBucket(): s3.Bucket {
    return this.bucket;
  }

  /**
   * Get CloudFront distribution for cache invalidation
   */
  getDistribution(): cloudfront.IDistribution | undefined {
    return this.distribution;
  }
}
