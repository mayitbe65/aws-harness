#!/usr/bin/env node

/**
 * CDK Application Entry Point
 * Instantiates the Error QA stacks for dev, staging, and production environments
 */

import "source-map-support/register";
import * as cdk from "aws-cdk-lib";
import { ErrorQaStack } from "../lib/stacks";
import { getConfig } from "../lib/config";
import * as dotenv from "dotenv";

// Load environment variables from .env file
dotenv.config();

const app = new cdk.App();

// Get environment from context or environment variable or default to dev
const env = app.node.tryGetContext("environment") || process.env.CDK_ENV || "dev";

console.log(`Deploying Error QA infrastructure for environment: ${env}`);

// Get configuration for the environment
const config = getConfig(env);

// AWS account and region
const awsEnv: cdk.Environment = {
  account: process.env.CDK_ACCOUNT || process.env.AWS_ACCOUNT_ID,
  region: config.region,
};

// Create Dev stack
if (env === "dev" || env === "all") {
  new ErrorQaStack(app, "ErrorQaStackDev", {
    config: getConfig("dev"),
    env: {
      account: awsEnv.account,
      region: "us-east-1",
    },
    description: "Error QA development environment stack",
    terminationProtection: false,
  });
}

// Create Staging stack
if (env === "staging" || env === "all") {
  new ErrorQaStack(app, "ErrorQaStackStaging", {
    config: getConfig("staging"),
    env: {
      account: awsEnv.account,
      region: "us-east-1",
    },
    description: "Error QA staging environment stack",
    terminationProtection: false,
  });
}

// Create Production stack
if (env === "prod" || env === "production" || env === "all") {
  new ErrorQaStack(app, "ErrorQaStackProd", {
    config: getConfig("prod"),
    env: {
      account: awsEnv.account,
      region: "us-east-1",
    },
    description: "Error QA production environment stack",
    terminationProtection: true, // Protect production stack from accidental deletion
  });
}

// Synth the app
app.synth();
